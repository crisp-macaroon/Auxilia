"""
OpenWeatherMap API Service
Fetches real-time weather data for parametric rain triggers
"""
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from app.core.config import settings
from app.models.schemas import WeatherData
import logging

logger = logging.getLogger(__name__)

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


class WeatherService:
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_current_weather(self, lat: float, lon: float) -> Optional[WeatherData]:
        """
        Get current weather data for a location.
        Returns rain amount in mm/h if raining.
        """
        try:
            url = f"{OPENWEATHER_BASE_URL}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract rain data (mm in last 1h and 3h)
            rain_1h = data.get("rain", {}).get("1h", 0.0)
            rain_3h = data.get("rain", {}).get("3h", 0.0)
            
            return WeatherData(
                zone_id="",  # Set by caller
                temperature=data["main"]["temp"],
                feels_like=data["main"]["feels_like"],
                humidity=data["main"]["humidity"],
                pressure=data["main"]["pressure"],
                wind_speed=data["wind"]["speed"],
                rain_1h=rain_1h,
                rain_3h=rain_3h,
                weather_main=data["weather"][0]["main"],
                weather_description=data["weather"][0]["description"],
                clouds=data["clouds"]["all"],
                visibility=data.get("visibility", 10000),
                heatwave_flag=(
                    data["main"].get("temp", 0.0) >= settings.HEATWAVE_TEMP_THRESHOLD_C
                    or data["main"].get("feels_like", 0.0) >= settings.HEATWAVE_TEMP_THRESHOLD_C
                ),
                timestamp=datetime.utcnow()
            )
        except httpx.HTTPError as e:
            logger.error(f"Weather API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Weather service error: {e}")
            return None
    
    async def get_weather_by_city(self, city: str, country: str = "IN") -> Optional[WeatherData]:
        """Get weather by city name"""
        try:
            url = f"{OPENWEATHER_BASE_URL}/weather"
            params = {
                "q": f"{city},{country}",
                "appid": self.api_key,
                "units": "metric"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            rain_1h = data.get("rain", {}).get("1h", 0.0)
            rain_3h = data.get("rain", {}).get("3h", 0.0)
            
            return WeatherData(
                zone_id="",
                temperature=data["main"]["temp"],
                feels_like=data["main"]["feels_like"],
                humidity=data["main"]["humidity"],
                pressure=data["main"]["pressure"],
                wind_speed=data["wind"]["speed"],
                rain_1h=rain_1h,
                rain_3h=rain_3h,
                weather_main=data["weather"][0]["main"],
                weather_description=data["weather"][0]["description"],
                clouds=data["clouds"]["all"],
                visibility=data.get("visibility", 10000),
                heatwave_flag=(
                    data["main"].get("temp", 0.0) >= settings.HEATWAVE_TEMP_THRESHOLD_C
                    or data["main"].get("feels_like", 0.0) >= settings.HEATWAVE_TEMP_THRESHOLD_C
                ),
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Weather by city error: {e}")
            return None
    
    async def get_forecast(self, lat: float, lon: float, hours: int = 24) -> list:
        """Get weather forecast for next N hours"""
        try:
            url = f"{OPENWEATHER_BASE_URL}/forecast"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "cnt": hours // 3  # API returns 3-hour intervals
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            forecasts = []
            for item in data.get("list", []):
                rain = item.get("rain", {}).get("3h", 0.0)
                forecasts.append({
                    "timestamp": datetime.fromtimestamp(item["dt"]),
                    "temperature": item["main"]["temp"],
                    "rain_3h": rain,
                    "weather": item["weather"][0]["main"],
                    "description": item["weather"][0]["description"]
                })
            
            return forecasts
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return []
    
    def is_rain_trigger_active(self, weather: WeatherData, threshold: float = None) -> bool:
        """Check if rain exceeds trigger threshold"""
        threshold = threshold or settings.RAIN_THRESHOLD_MM
        return weather.rain_1h >= threshold or weather.rain_3h >= threshold
    
    async def close(self):
        await self.client.aclose()


weather_service = WeatherService()
