import httpx
from typing import Optional, Dict, Any

class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def get_weather(self, city: str) -> Optional[Dict[str, Any]]:
        # Fallback to mock data if API key is not configured/dummy
        if not self.api_key or self.api_key.lower() == "dummy":
            return {
                "city": city.capitalize(),
                "temperature": 24.5,
                "description": "clear sky (mocked)",
                "humidity": 55,
                "wind_speed": 4.1
            }
            
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "city": data.get("name", city).capitalize(),
                        "temperature": float(data["main"]["temp"]),
                        "description": data["weather"][0]["description"],
                        "humidity": int(data["main"]["humidity"]),
                        "wind_speed": float(data["wind"]["speed"])
                    }
                return None
        except Exception:
            # Fallback to mock data if OpenWeather request fails
            return {
                "city": city.capitalize(),
                "temperature": 24.5,
                "description": "clear sky (mocked fallback)",
                "humidity": 55,
                "wind_speed": 4.1
            }
