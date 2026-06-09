import json
import asyncio
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.services.retrieval_service import RetrievalService
from app.services.embedding_service import EmbeddingService
from app.services.weather_service import WeatherService
from app.services.wikipedia_service import WikipediaService
from app.services.llm_service import LLMService
from app.schemas.schemas import TripPlanRequest, TripPlanResponse, DayPlan


class TravelPlannerService:
    """
    Orchestrates the full RAG-based itinerary generation pipeline:
      1. Parallel fetch: weather + Wikipedia
      2. pgvector similarity search for local DB context
      3. LLM prompt construction (context-grounded, no hallucination)
      4. JSON parsing + response assembly
    """

    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        weather_service: WeatherService,
        wikipedia_service: WikipediaService,
    ):
        self.retrieval = RetrievalService(db, embedding_service)
        self.llm = llm_service
        self.weather = weather_service
        self.wiki = wikipedia_service

    async def generate_itinerary(self, req: TripPlanRequest) -> TripPlanResponse:
        # 1. Parallel external fetches
        weather_info, wiki_summary = await asyncio.gather(
            self.weather.get_weather(req.destination),
            self.wiki.get_summary(req.destination),
        )

        # 2. Semantic retrieval from pgvector
        search_query = f"{req.destination} {req.preferences or ''}".strip()
        results = self.retrieval.search_similar(search_query, limit=5)

        # Filter: keep only entries that mention the destination (case-insensitive)
        dest_lower = req.destination.lower()
        matched = [
            d for d in results
            if dest_lower in d.name.lower() or dest_lower in d.description.lower()
        ]

        has_db_ctx = len(matched) > 0
        has_wiki_ctx = bool(wiki_summary)

        if not has_db_ctx and not has_wiki_ctx:
            raise ValueError("Data not available")

        # 3. Build context strings
        db_ctx = "\n\n".join(
            f"- [{d.category.upper()}] {d.name}: {d.description}" for d in matched
        ) or "None available"

        wiki_ctx = wiki_summary or "None available"

        weather_ctx = (
            f"{weather_info['city']}: {weather_info['description']}, "
            f"{weather_info['temperature']}°C, humidity {weather_info['humidity']}%, "
            f"wind {weather_info['wind_speed']} m/s"
            if weather_info else "No weather data available"
        )

        # 4. Construct strict JSON prompt
        prompt = f"""You are a professional local travel planning assistant.

TASK: Generate a {req.days}-day travel itinerary for {req.destination} with a {req.budget} budget.

RULES:
- Use ONLY the Database Context and Wikipedia Context provided below.
- Do NOT hallucinate places, activities, prices, or facts.
- If context is insufficient, return exactly: {{"error": "Data not available"}}

Database Context:
{db_ctx}

Wikipedia Context:
{wiki_ctx}

Weather at {req.destination}:
{weather_ctx}

User Preferences: {req.preferences or "None"}

OUTPUT FORMAT (raw JSON only, no markdown, no explanation):
{{
  "destination": "{req.destination}",
  "budget": "{req.budget}",
  "days": {req.days},
  "itinerary": [
    {{
      "day": 1,
      "theme": "string",
      "activities": ["string", "string"],
      "recommended_food": ["string"],
      "recommended_stay": "string",
      "estimated_cost": "e.g. $30-$60 per day"
    }}
  ]
}}"""

        raw = await self.llm.generate_response(prompt)
        raw = raw.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(
                l for l in lines if not l.strip().startswith("```")
            ).strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}. Raw output: {raw[:200]}")

        if "error" in data:
            raise ValueError(data["error"])

        itinerary = [DayPlan(**day) for day in data.get("itinerary", [])]

        return TripPlanResponse(
            destination=req.destination,
            budget=req.budget,
            days=req.days,
            weather=weather_info,
            itinerary=itinerary,
            wikipedia_summary=wiki_summary,
        )
