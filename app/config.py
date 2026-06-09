import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./travel_planner.db")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "dummy")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
