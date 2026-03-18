"""
Auxilia Services
Real API integrations for parametric insurance triggers
"""
from app.services.weather_service import weather_service, WeatherService
from app.services.traffic_service import traffic_service, TrafficService
from app.services.location_service import location_service, LocationService
from app.services.news_service import news_service, NewsService
from app.services.surge_service import surge_service, SurgeService

__all__ = [
    "weather_service",
    "WeatherService",
    "traffic_service", 
    "TrafficService",
    "location_service",
    "LocationService",
    "news_service",
    "NewsService",
    "surge_service",
    "SurgeService",
]
