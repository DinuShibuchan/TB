# AI Travel Planner — RAG-Powered Itinerary Generator

A production-quality REST API and interactive dashboard that generates personalized travel itineraries using Retrieval-Augmented Generation (RAG). Built with FastAPI, PostgreSQL + pgvector, sentence-transformers, and a local Ollama LLM.

---

## Features

| Feature | Description |
|---|---|
| **RAG Itinerary Planner** | Generates day-wise travel plans grounded in local database context + Wikipedia + weather |
| **Semantic Vector Search** | Stores travel knowledge as 384-dim embeddings via pgvector; retrieves top-5 similar entries |
| **Context-Aware Chat** | Assistant answers questions strictly from retrieved database context — no hallucination |
| **Weather Integration** | Real-time weather via OpenWeather API (with offline mock fallback) |
| **Auto-Seeded Database** | 10 sample entries (Tokyo, Paris, Rome, Munnar) inserted automatically on first run |
| **Interactive Frontend** | Premium dark-mode dashboard with glassmorphism UI served on the same port |
| **One-Command Startup** | `npm start` launches both backend API and frontend |

---

## Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL 15+ with pgvector extension
- **ORM**: SQLAlchemy 2.x
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`, 384 dimensions)
- **LLM**: Ollama (local, `mistral` or `llama3`)
- **HTTP Client**: httpx (async)
- **Validation**: Pydantic v2

---

## Architecture — RAG Flow

```
User Request ──> FastAPI Route
                    │
                    ├──> Embedding Service (query → 384-dim vector)
                    │         │
                    │         └──> pgvector similarity search (top-5 results)
                    │
                    ├──> Wikipedia REST API (destination summary)
                    │
                    ├──> OpenWeather API (current conditions)
                    │
                    └──> Ollama LLM
                           │
                           ├── System prompt enforces: use ONLY retrieved context
                           ├── Zero temperature (deterministic, no hallucination)
                           └── Output: structured JSON itinerary
```

**Key rule**: If no context is found in the database AND Wikipedia returns nothing, the API returns `404 — "Data not available"` instead of generating hallucinated content.

---

## Project Structure

```
AI PROJECT/
├── app/
│   ├── api/
│   │   └── routes.py              # API endpoints (thin — delegates to services)
│   ├── db/
│   │   ├── database.py            # SQLAlchemy engine, session, Base
│   │   └── seeder.py              # Auto-seeds 10 travel entries on first run
│   ├── models/
│   │   └── models.py              # Destination (with pgvector), ChatHistory
│   ├── schemas/
│   │   └── schemas.py             # Pydantic input/output schemas
│   ├── services/
│   │   ├── embedding_service.py   # sentence-transformers wrapper
│   │   ├── llm_service.py         # Ollama /api/generate client
│   │   ├── planner_service.py     # Orchestrates full RAG pipeline
│   │   ├── retrieval_service.py   # pgvector add + similarity search
│   │   ├── weather_service.py     # OpenWeather with mock fallback
│   │   └── wikipedia_service.py   # Wikipedia REST API client
│   ├── config.py                  # pydantic-settings env loader
│   └── main.py                    # App factory, lifespan, static mount
├── frontend/
│   ├── index.html                 # Dashboard layout
│   ├── style.css                  # Dark glassmorphism theme
│   └── app.js                     # Client-side API integration
├── .env                           # Environment variables
├── package.json                   # npm start → uvicorn
├── requirements.txt               # Python dependencies
├── verify_rag.py                  # End-to-end RAG test script
└── README.md                      # This file
```

---

## Local Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install and Configure PostgreSQL with pgvector

1. Install PostgreSQL 15+ from [postgresql.org](https://www.postgresql.org/download/)
2. Install the pgvector extension:
   - **Windows**: Download from [pgvector releases](https://github.com/pgvector/pgvector/releases) and copy files to your PostgreSQL installation
   - **macOS**: `brew install pgvector`
   - **Linux**: `sudo apt install postgresql-16-pgvector`
3. Create the database:
   ```sql
   CREATE DATABASE travel_planner;
   ```
4. Enable pgvector (the app also does this automatically on startup):
   ```sql
   \c travel_planner
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### 3. Install and Run Ollama

1. Download from [ollama.com](https://ollama.com/)
2. Pull a model:
   ```bash
   ollama pull mistral
   ```
3. Verify Ollama is running:
   ```bash
   curl http://localhost:11434/api/version
   ```

### 4. Configure Environment

Edit `.env` in the project root:

```ini
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/travel_planner
OPENWEATHER_API_KEY=dummy
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

> **Note**: Set `OPENWEATHER_API_KEY=dummy` for mocked weather data, or use a real key from [openweathermap.org](https://openweathermap.org/api).

### 5. Start the Application

```bash
npm start
```

This runs `python -m uvicorn app.main:app --reload` — serving both the API and frontend on `http://localhost:8000`.

- **Dashboard UI**: http://localhost:8000/
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Documentation

### `GET /health`

Returns system connection status.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "database": "healthy",
  "embedding_model": "all-MiniLM-L6-v2",
  "ollama_url": "http://localhost:11434",
  "timestamp": "2026-06-09T14:00:00.000000"
}
```

---

### `POST /add-data`

Inserts travel context into the RAG database with auto-generated embeddings.

```bash
curl -X POST http://localhost:8000/add-data \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Munnar",
    "description": "Eravikulam National Park hosts the endangered Nilgiri Tahr and offers stunning mountain views.",
    "category": "place"
  }'
```

```json
{
  "id": 11,
  "name": "Munnar",
  "description": "Eravikulam National Park hosts the endangered Nilgiri Tahr...",
  "category": "place"
}
```

---

### `POST /plan-trip`

Generates a structured, day-wise itinerary using RAG context.

```bash
curl -X POST http://localhost:8000/plan-trip \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Tokyo",
    "budget": "Moderate",
    "days": 2,
    "preferences": "temples and local food"
  }'
```

```json
{
  "destination": "Tokyo",
  "budget": "Moderate",
  "days": 2,
  "weather": {
    "city": "Tokyo",
    "temperature": 24.5,
    "description": "clear sky",
    "humidity": 55,
    "wind_speed": 4.1
  },
  "itinerary": [
    {
      "day": 1,
      "theme": "Historical Asakusa & Local Food",
      "activities": ["Visit Senso-ji Temple", "Walk Nakamise shopping street"],
      "recommended_food": ["Tonkotsu ramen at Ichiran"],
      "recommended_stay": "Khaosan Tokyo Origami hostel",
      "estimated_cost": "$40-$70 per day"
    }
  ],
  "wikipedia_summary": "Tokyo is the capital of Japan..."
}
```

---

### `POST /chat`

Context-aware chat — retrieves semantically similar database entries before answering.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me hidden places in Munnar"}'
```

```json
{
  "query": "Tell me hidden places in Munnar",
  "response": "Secret Valley Waterfall is a hidden gem in Munnar, located 14 km off the main road...",
  "timestamp": "2026-06-09T14:10:00.000000"
}
```

---

### `GET /weather/{city}`

Returns current weather data for a city.

```bash
curl http://localhost:8000/weather/paris
```

```json
{
  "city": "Paris",
  "temperature": 18.3,
  "description": "partly cloudy",
  "humidity": 62,
  "wind_speed": 3.5
}
```

---

## Testing

### Automated RAG Verification

After starting the server, run the end-to-end test suite:

```bash
python verify_rag.py
```

This script:
1. Checks `/health` endpoint
2. Inserts a Munnar "Secret Valley Waterfall" entry via `/add-data`
3. Queries `/chat` with "Tell me hidden places in Munnar" and verifies the RAG system retrieves the inserted data
4. Tests `/plan-trip` JSON structure (including `estimated_cost`)
5. Validates `/weather` responses
6. Tests edge cases (invalid input rejection)

### Manual Testing via Swagger

1. Open http://localhost:8000/docs
2. Use the interactive "Try it out" buttons on each endpoint
3. Verify responses match the expected formats above

---

## Error Handling

| HTTP Code | Meaning |
|---|---|
| `200` | Success |
| `201` | Data created successfully |
| `400` | Bad request (empty city name, etc.) |
| `404` | Data not available — RAG found no matching context |
| `422` | Validation error (Pydantic) or LLM returned invalid JSON |
| `500` | Internal server error |
| `503` | Database offline — PostgreSQL not reachable |

---

## Sample Seed Data (Auto-Loaded)

The application automatically seeds 10 travel entries on first startup:

| Destination | Category | Highlights |
|---|---|---|
| Tokyo | Place | Senso-ji Temple, Shibuya Crossing |
| Tokyo | Food | Ichiran Ramen, Tsukiji Market sushi |
| Tokyo | Stay | Khaosan hostel, Park Hyatt |
| Paris | Place | Eiffel Tower, Louvre Museum |
| Paris | Food | Croissants, L'As du Fallafel |
| Rome | Place | Colosseum, Roman Forum |
| Rome | Food | Cacio e Pepe, Fatamorgana gelato |
| Munnar | Place | Secret Valley Waterfall (RAG test entry) |
| Munnar | Place | Tea plantations, Eravikulam National Park |

---

## Production Deployment (GitHub & Render)

This project is configured with a Render Blueprint [`render.yaml`](file:///c:/AI%20PROJECT/render.yaml) to deploy a Web Service and a PostgreSQL database on Render automatically.

### 1. Push to GitHub
Initialize your local git repository, commit the files, and push them to a new GitHub repository:

```bash
git init
git add .
git commit -m "Configure project for GitHub and Render deployment"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

### 2. Deploy via Render Blueprint
1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Click **New** (top right) and select **Blueprint**.
3. Select your connected GitHub repository.
4. Render will read [`render.yaml`](file:///c:/AI%20PROJECT/render.yaml) and automatically deploy both the PostgreSQL database (pgvector ready) and the FastAPI web service, linking them together via the `DATABASE_URL` environment variable.
