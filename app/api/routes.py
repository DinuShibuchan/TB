from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from datetime import datetime, timezone

from app.db.database import get_db
from app.models.models import ChatHistory
from app.services.retrieval_service import RetrievalService
from app.services.planner_service import TravelPlannerService
from app.schemas.schemas import (
    DestinationCreate,
    DestinationResponse,
    TripPlanRequest,
    TripPlanResponse,
    ChatRequest,
    ChatResponse,
    WeatherResponse,
    HealthResponse,
)

router = APIRouter()

# ─── Utility ──────────────────────────────────────────────────────────────────

def _db_error():
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Database connection error. "
            "Please ensure PostgreSQL is running and pgvector is enabled. "
            "Run: CREATE EXTENSION IF NOT EXISTS vector; in your database."
        ),
    )


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(request: Request, db: Session = Depends(get_db)):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)[:120]}"

    cfg = request.app.state
    db_type = getattr(cfg, "database_type", "postgresql")

    ollama_status = "unknown"
    llm_service = getattr(cfg, "llm_service", None)
    if llm_service:
        is_online = await llm_service.check_connection()
        ollama_status = "online" if is_online else "offline"

    return HealthResponse(
        status="ok" if db_status == "healthy" else "degraded",
        database=db_status,
        embedding_model="all-MiniLM-L6-v2",
        ollama_url=getattr(cfg, "ollama_url", "http://localhost:11434"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        database_type=db_type,
        ollama_status=ollama_status,
    )


# ─── Add Data ─────────────────────────────────────────────────────────────────

@router.post(
    "/add-data",
    response_model=DestinationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["RAG Database"],
)
def add_data(data: DestinationCreate, request: Request, db: Session = Depends(get_db)):
    embedding_svc = request.app.state.embedding_service
    retrieval = RetrievalService(db, embedding_svc)

    try:
        dest = retrieval.add_destination(
            name=data.name,
            description=data.description,
            category=data.category,
        )
        return dest
    except OperationalError:
        _db_error()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add data: {str(e)}",
        )


# ─── Plan Trip ────────────────────────────────────────────────────────────────

@router.post("/plan-trip", response_model=TripPlanResponse, tags=["Planner"])
async def plan_trip(
    trip_req: TripPlanRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    state = request.app.state
    planner = TravelPlannerService(
        db=db,
        embedding_service=state.embedding_service,
        llm_service=state.llm_service,
        weather_service=state.weather_service,
        wikipedia_service=state.wikipedia_service,
    )

    try:
        return await planner.generate_itinerary(trip_req)
    except OperationalError:
        _db_error()
    except ValueError as e:
        err = str(e)
        if "Data not available" in err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Itinerary generation error: {str(e)}",
        )


# ─── Chat ─────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    chat_req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    state = request.app.state
    retrieval = RetrievalService(db, state.embedding_service)

    try:
        # Retrieve top-5 semantically similar context entries
        results = retrieval.search_similar(chat_req.query, limit=5)
    except OperationalError:
        _db_error()

    # Get Wikipedia context based on first matched entry
    wiki_summary = None
    if results:
        wiki_summary = await state.wikipedia_service.get_summary(results[0].name)

    has_db_ctx = len(results) > 0
    has_wiki_ctx = bool(wiki_summary)

    # Short-circuit: no context at all
    if not has_db_ctx and not has_wiki_ctx:
        response_text = "Data not available"
    else:
        db_ctx = "\n\n".join(
            f"- [{d.category.upper()}] {d.name}: {d.description}" for d in results
        )
        prompt = f"""You are a professional local travel assistant.
Answer the user's query using ONLY the Database Context and Wikipedia Context below.
Do NOT hallucinate facts, prices, or places.
If the context does not answer the query, reply exactly: "Data not available"
Keep your answer concise (3–5 sentences max).

Database Context:
{db_ctx}

Wikipedia Context:
{wiki_summary or "None available"}

User Query: {chat_req.query}
"""
        response_text = await state.llm_service.generate_response(prompt)
        response_text = response_text.strip() or "Data not available"

    # Persist to chat_history
    try:
        record = ChatHistory(query=chat_req.query, response=response_text)
        db.add(record)
        db.commit()
        db.refresh(record)
        return ChatResponse(
            query=record.query,
            response=record.response,
            timestamp=record.timestamp,
        )
    except OperationalError:
        # Return without persisting if DB is down
        return ChatResponse(
            query=chat_req.query,
            response=response_text,
            timestamp=datetime.now(timezone.utc),
        )


# ─── Weather ──────────────────────────────────────────────────────────────────

@router.get("/weather/{city}", response_model=WeatherResponse, tags=["Weather"])
async def get_weather(city: str, request: Request):
    if not city.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="City name cannot be empty.",
        )

    weather = await request.app.state.weather_service.get_weather(city.strip())

    if not weather:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Weather data for '{city}' not found.",
        )

    return WeatherResponse(**weather)
