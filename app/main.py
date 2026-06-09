import os
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI(title="AI Travel Planner")

# Serve static files (index.html etc.)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Example: include routers if they exist
# from app.api.routes import router as api_router
# app.include_router(api_router, prefix="/api")
