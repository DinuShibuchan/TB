import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.database import engine, Base, SessionLocal
from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.weather_service import WeatherService
from app.services.wikipedia_service import WikipediaService
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 1. Load embedding model (always, even if DB is offline) ──────────────
    try:
        print("[Startup] Loading sentence-transformers model (all-MiniLM-L6-v2)...")
        app.state.embedding_service = EmbeddingService()
        print("[Startup] Embedding model loaded.")
    except Exception as e:
        print(f"[Startup] ERROR: Could not load embedding model: {e}")
        app.state.embedding_service = None

    # ── 2. Attach all other services ─────────────────────────────────────────
    app.state.llm_service = LLMService(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
    )
    # Check Ollama connectivity on startup
    try:
        await app.state.llm_service.check_connection()
    except Exception:
        app.state.llm_service.ollama_online = False

    app.state.weather_service = WeatherService(api_key=settings.OPENWEATHER_API_KEY)
    app.state.wikipedia_service = WikipediaService()
    app.state.ollama_url = settings.OLLAMA_BASE_URL

    # ── 3. Database initialisation (fallback to SQLite if Postgres is offline) ─
    database_type = "postgresql"
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
        print("[Startup] PostgreSQL database schema verified / created.")
    except Exception as e:
        database_type = "sqlite"
        print(f"[Startup] PostgreSQL connection failed. Falling back to SQLite... Error: {str(e)[:200]}")
        from sqlalchemy import create_engine
        import app.db.database as database
        sqlite_url = "sqlite:///./travel_planner.db"
        database.engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        database.SessionLocal.configure(bind=database.engine)
        database.Base.metadata.create_all(bind=database.engine)
        print("[Startup] SQLite database initialized successfully.")

    app.state.database_type = database_type

    # ── 4. Seed sample data on first run ──────────────────────────────────────
    if app.state.embedding_service is not None:
        try:
            from app.db.seeder import seed_database
            import app.db.database as database
            db = database.SessionLocal()
            try:
                seed_database(db, app.state.embedding_service)
            finally:
                db.close()
        except Exception as seed_err:
            print(f"[Startup] Seeder warning: {seed_err}")

    yield  # ── Application runs ──────────────────────────────────────────────


# ── App Factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Travel Planner API",
    description=(
        "Production-quality RAG-based travel itinerary planner. "
        "Uses local Ollama LLM, PostgreSQL + pgvector, and external APIs."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ────────────────────────────────────────────────────────────────

app.include_router(router)

# ── Static Frontend ───────────────────────────────────────────────────────────

os.makedirs("frontend", exist_ok=True)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", include_in_schema=False)
def serve_ui():
    index = os.path.join("frontend", "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {
        "message": "AI Travel Planner API is running.",
        "docs": "/docs",
        "health": "/health",
    }
