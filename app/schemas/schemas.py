from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# ─── Input Schemas ────────────────────────────────────────────────────────────

class DestinationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the destination/city")
    description: str = Field(..., min_length=1, description="Travel details, tips, food, or general info")
    category: str = Field(..., pattern="^(place|food|stay)$", description="Category: place, food, or stay")

class TripPlanRequest(BaseModel):
    destination: str = Field(..., min_length=1, description="Name of the destination city/country")
    budget: str = Field(..., min_length=1, description="Budget category e.g. Budget, Moderate, Luxury")
    days: int = Field(..., gt=0, le=30, description="Number of days for the trip (1-30)")
    preferences: Optional[str] = Field(None, description="Travel preferences e.g. adventure, food, history")

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question or query")

# ─── Output Schemas ───────────────────────────────────────────────────────────

class DestinationResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str

    class Config:
        from_attributes = True

class DayPlan(BaseModel):
    day: int = Field(..., description="Day number")
    theme: str = Field(..., description="Daily theme or highlight")
    activities: List[str] = Field(..., description="List of activities for the day")
    recommended_food: List[str] = Field(..., description="Recommended food/restaurants for the day")
    recommended_stay: Optional[str] = Field(None, description="Recommended accommodation option")
    estimated_cost: Optional[str] = Field(None, description="Estimated daily cost range e.g. $30-$60")

class TripPlanResponse(BaseModel):
    destination: str
    budget: str
    days: int
    weather: Optional[dict] = Field(None, description="Current weather data at destination")
    itinerary: List[DayPlan] = Field(..., description="Day-by-day structured itinerary")
    wikipedia_summary: Optional[str] = Field(None, description="Brief summary from Wikipedia")

class ChatResponse(BaseModel):
    query: str
    response: str
    timestamp: datetime

    class Config:
        from_attributes = True

class WeatherResponse(BaseModel):
    city: str
    temperature: float
    description: str
    humidity: int
    wind_speed: float

class HealthResponse(BaseModel):
    status: str
    database: str
    embedding_model: str
    ollama_url: str
    timestamp: str
    database_type: Optional[str] = None
    ollama_status: Optional[str] = None
