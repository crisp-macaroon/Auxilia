"""
Weather API Router
Dedicated endpoints for weather data and forecasts
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional

from app.services.weather_service import weather_service
from app.agents.trigger_agent import ZONE_CONFIG
from app.core.config import settings

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/current/{zone_id}")
async def get_current_weather(zone_id: str):
    """Get current weather for a zone."""
    if zone_id not in ZONE_CONFIG:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone = ZONE_CONFIG[zone_id]
    weather = await weather_service.get_current_weather(zone["lat"], zone["lon"])
    
    if not weather:
        raise HTTPException(status_code=503, detail="Weather service unavailable")
    
    weather.zone_id = zone_id
    
    return {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "city": zone["city"],
        "weather": weather.model_dump(),
        "rain_trigger": {
            "threshold_mm": settings.RAIN_THRESHOLD_MM,
            "is_active": weather_service.is_rain_trigger_active(weather),
            "current_rain_1h": weather.rain_1h,
            "current_rain_3h": weather.rain_3h
        }
    }


@router.get("/city/{city}")
async def get_weather_by_city(city: str, country: str = "IN"):
    """Get current weather by city name."""
    weather = await weather_service.get_weather_by_city(city, country)
    
    if not weather:
        raise HTTPException(status_code=503, detail="Weather service unavailable")
    
    return {
        "city": city,
        "country": country,
        "weather": weather.model_dump(),
        "rain_trigger_active": weather_service.is_rain_trigger_active(weather)
    }


@router.get("/forecast/{zone_id}")
async def get_weather_forecast(zone_id: str, hours: int = 24):
    """Get weather forecast for a zone."""
    if zone_id not in ZONE_CONFIG:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone = ZONE_CONFIG[zone_id]
    forecast = await weather_service.get_forecast(zone["lat"], zone["lon"], hours)
    
    # Analyze forecast for rain triggers
    rain_windows = []
    for item in forecast:
        if item.get("rain_3h", 0) >= settings.RAIN_THRESHOLD_MM:
            rain_windows.append({
                "timestamp": item["timestamp"].isoformat(),
                "rain_mm": item["rain_3h"],
                "weather": item["weather"]
            })
    
    return {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "forecast": forecast,
        "rain_trigger_windows": rain_windows,
        "hours_covered": hours
    }


@router.get("/all-zones")
async def get_all_zones_weather():
    """Get current weather for all configured zones."""
    results = {}
    
    for zone_id, zone in ZONE_CONFIG.items():
        weather = await weather_service.get_current_weather(zone["lat"], zone["lon"])
        
        if weather:
            results[zone_id] = {
                "name": zone["name"],
                "city": zone["city"],
                "temperature": weather.temperature,
                "weather_main": weather.weather_main,
                "rain_1h": weather.rain_1h,
                "rain_trigger_active": weather_service.is_rain_trigger_active(weather)
            }
        else:
            results[zone_id] = {
                "name": zone["name"],
                "city": zone["city"],
                "error": "Data unavailable"
            }
    
    return {
        "zones": results,
        "total_zones": len(ZONE_CONFIG),
        "zones_with_rain_trigger": len([
            z for z in results.values() 
            if z.get("rain_trigger_active", False)
        ]),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/rain-alerts")
async def get_rain_alerts():
    """Get zones with active or imminent rain triggers."""
    alerts = []
    
    for zone_id, zone in ZONE_CONFIG.items():
        weather = await weather_service.get_current_weather(zone["lat"], zone["lon"])
        
        if weather and weather_service.is_rain_trigger_active(weather):
            alerts.append({
                "zone_id": zone_id,
                "zone_name": zone["name"],
                "city": zone["city"],
                "rain_1h": weather.rain_1h,
                "rain_3h": weather.rain_3h,
                "weather": weather.weather_description,
                "severity": "high" if max(weather.rain_1h, weather.rain_3h) > settings.RAIN_THRESHOLD_MM * 2 else "medium"
            })
    
    return {
        "alerts": alerts,
        "count": len(alerts),
        "threshold_mm": settings.RAIN_THRESHOLD_MM,
        "timestamp": datetime.utcnow().isoformat()
    }
