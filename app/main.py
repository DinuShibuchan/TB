import os
from fastapi import FastAPI
from dotenv import load_dotenv

# Load .env variables (optional for local dev)
load_dotenv()

app = FastAPI(title="AI Travel Planner")

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Example: include routers if they exist
# from app.api.routes import router as api_router
# app.include_router(api_router, prefix="/api")
