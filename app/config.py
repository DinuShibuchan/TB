from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/travel_planner"
    OPENWEATHER_API_KEY: str = "dummy"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
