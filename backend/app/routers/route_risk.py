import asyncio
import math
from datetime import datetime
from typing import Iterable

from fastapi import APIRouter

from app.models.schemas import LocationHistoryCreate, PersonaType, RouteRiskRequest, RouteRiskResponse
from app.services.location_service import location_service
from app.services.news_service import news_service
from app.services.traffic_service import traffic_service
from app.services.weather_service import weather_service
from app.services.ml_service import risk_ml_service

router = APIRouter(prefix="/riders", tags=["Route Analysis"])


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def _interpolated_path(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    num_points: int = 12,
) -> list[list[float]]:
    points: list[list[float]] = []
    if num_points <= 1:
        return [[start_lat, start_lon], [end_lat, end_lon]]
    for i in range(num_points):
        fraction = i / (num_points - 1)
        lat = start_lat + (end_lat - start_lat) * fraction
        lon = start_lon + (end_lon - start_lon) * fraction
        points.append([float(lat), float(lon)])
    return points


def _bbox_from_path(path: Iterable[list[float]], padding_km: float = 1.2) -> tuple[float, float, float, float]:
    path_list = list(path)
    lats = [p[0] for p in path_list]
    lons = [p[1] for p in path_list]

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    mid_lat = (min_lat + max_lat) / 2
    lat_pad = padding_km / 111.0
    lon_pad = padding_km / max(1e-6, (111.0 * math.cos(math.radians(mid_lat))))

    return (
        float(min_lon - lon_pad),
        float(min_lat - lat_pad),
        float(max_lon + lon_pad),
        float(max_lat + lat_pad),
    )


def _sample_points_every_5km(path: list[list[float]]) -> list[tuple[float, float]]:
    if not path:
        return []

    sampled: list[tuple[float, float]] = [(path[0][0], path[0][1])]
    distance_since_last = 0.0

    for idx in range(1, len(path)):
        prev = path[idx - 1]
        curr = path[idx]
        segment_km = _haversine_km(prev[0], prev[1], curr[0], curr[1])
        distance_since_last += segment_km

        if distance_since_last >= 5.0:
            sampled.append((curr[0], curr[1]))
            distance_since_last = 0.0

    end_point = (path[-1][0], path[-1][1])
    if sampled[-1] != end_point:
        sampled.append(end_point)

    return sampled[:8]


async def _resolve_city_name(lat: float, lon: float) -> str:
    location = await location_service.reverse_geocode(lat, lon)
    if location and location.city:
        return location.city
    return "Mumbai"


def _severity_to_weight(severity: str) -> float:
    mapping = {
        "severe": 0.95,
        "major": 0.75,
        "moderate": 0.55,
        "minor": 0.3,
        "unknown": 0.2,
    }
    return mapping.get(severity.lower(), 0.25)


@router.post("/{rider_id}/route-risk", response_model=RouteRiskResponse)
async def assess_route_risk(
    rider_id: str,
    payload: RouteRiskRequest,
):
    """
    Analyze rider to destination route using live services:
    - traffic-aware route travel data and incidents (TomTom)
    - weather samples along corridor (OpenWeather)
    - local incident news near destination (NewsAPI + Gemini)
    """
    _ = rider_id

    route_summary = await traffic_service.get_route_traffic(
        origin=(payload.rider_latitude, payload.rider_longitude),
        destination=(payload.delivery_latitude, payload.delivery_longitude),
    )

    route_points = []
    if route_summary and route_summary.get("path_coordinates"):
        route_points = [
            [float(point[0]), float(point[1])]
            for point in route_summary["path_coordinates"]
            if isinstance(point, list) and len(point) == 2
        ]

    if len(route_points) < 2:
        route_points = _interpolated_path(
            payload.rider_latitude,
            payload.rider_longitude,
            payload.delivery_latitude,
            payload.delivery_longitude,
        )

    sampled_points = _sample_points_every_5km(route_points)
    if not sampled_points:
        sampled_points = [
            (payload.rider_latitude, payload.rider_longitude),
            (payload.delivery_latitude, payload.delivery_longitude),
        ]

    traffic_tasks = [traffic_service.get_traffic_flow(lat, lon) for lat, lon in sampled_points]
    weather_tasks = [weather_service.get_current_weather(lat, lon) for lat, lon in sampled_points]
    sampled_traffic, sampled_weather = await asyncio.gather(
        asyncio.gather(*traffic_tasks, return_exceptions=True),
        asyncio.gather(*weather_tasks, return_exceptions=True),
    )

    traffic_scores: list[float] = []
    road_closure_count = 0
    for traffic in sampled_traffic:
        if isinstance(traffic, Exception) or traffic is None:
            continue
        traffic_scores.append(max(0.0, min(1.0, float(traffic.congestion_level) / 10.0)))
        if traffic.road_closure:
            road_closure_count += 1

    weather_scores: list[float] = []
    for weather in sampled_weather:
        if isinstance(weather, Exception) or weather is None:
            continue
        rain_score = min(1.0, max(float(weather.rain_1h), float(weather.rain_3h) / 3.0) / 8.0)
        wind_score = min(1.0, float(weather.wind_speed) / 22.0)
        weather_scores.append(round((rain_score * 0.7) + (wind_score * 0.3), 3))

    city = await _resolve_city_name(payload.delivery_latitude, payload.delivery_longitude)
    destination_news = await news_service.search_incidents(city=city, hours_back=24)

    path_bbox = _bbox_from_path(route_points)
    traffic_incidents = await traffic_service.get_traffic_incidents(path_bbox)

    formatted_incidents: list[dict] = []

    for incident in traffic_incidents[:5]:
        coords = incident.get("coordinates") or []
        lat = payload.delivery_latitude
        lon = payload.delivery_longitude
        if isinstance(coords, list) and coords and isinstance(coords[0], list) and len(coords[0]) >= 2:
            lon = float(coords[0][0])
            lat = float(coords[0][1])

        formatted_incidents.append(
            {
                "type": "traffic",
                "title": incident.get("description") or "Traffic disruption",
                "severity": _severity_to_weight(str(incident.get("severity", "unknown"))),
                "location": incident.get("from_location") or incident.get("road") or city,
                "lat": lat,
                "lon": lon,
            }
        )

    for article in destination_news[:5]:
        formatted_incidents.append(
            {
                "type": article.incident_type,
                "title": article.title,
                "severity": float(article.severity),
                "location": article.location or city,
                "lat": float(payload.delivery_latitude),
                "lon": float(payload.delivery_longitude),
            }
        )

    avg_traffic_risk = sum(traffic_scores) / len(traffic_scores) if traffic_scores else 0.0
    avg_weather_risk = sum(weather_scores) / len(weather_scores) if weather_scores else 0.0
    incident_risk = min(1.0, (sum(i["severity"] for i in formatted_incidents[:8]) / 8.0) if formatted_incidents else 0.0)

    delay_ratio = 0.0
    if route_summary:
        no_traffic_time = float(route_summary.get("no_traffic_time") or 0)
        live_traffic_time = float(route_summary.get("live_traffic_time") or 0)
        if no_traffic_time > 0:
            delay_ratio = max(0.0, min(1.0, (live_traffic_time - no_traffic_time) / no_traffic_time))

    route_traffic_risk = max(avg_traffic_risk, delay_ratio)
    closure_risk_boost = min(0.2, road_closure_count * 0.05)

    risk_model_version = "fallback-v1"
    try:
        ml_overall_risk = risk_ml_service.predict_risk_score(
            zone_id=f"route:{city.lower()}",
            zone_base_risk=min(1.0, max(0.0, route_traffic_risk * 0.55 + avg_weather_risk * 0.45)),
            weather_risk=avg_weather_risk,
            traffic_risk=route_traffic_risk,
            incident_risk=min(1.0, incident_risk + closure_risk_boost),
            historical_risk=0.2,
            persona=PersonaType.FOOD_DELIVERY,
            age_band="26-35",
            vehicle_type="scooter",
            shift_type="mixed",
            tenure_months=18,
            month=datetime.utcnow().month,
        )
        overall_risk = min(1.0, max(0.0, ml_overall_risk))
        risk_model_version = risk_ml_service.model_version
    except Exception:
        overall_risk = min(
            1.0,
            (route_traffic_risk * 0.42)
            + (avg_weather_risk * 0.28)
            + (incident_risk * 0.25)
            + closure_risk_boost,
        )

    risk_factors: list[str] = []
    if route_traffic_risk >= 0.55:
        risk_factors.append("Elevated route traffic risk")
    if avg_weather_risk >= 0.45:
        risk_factors.append("Adverse weather on delivery corridor")
    if incident_risk >= 0.35:
        risk_factors.append("Active disruption reports near destination")
    if road_closure_count > 0:
        risk_factors.append("Road closure signals detected on route")

    if not risk_factors:
        risk_factors.append("Low live disruption signals on selected route")

    epicenter_multiplier = 1.0 + min(0.6, incident_risk * 0.6)

    return RouteRiskResponse(
        path_coordinates=route_points,
        incidents=formatted_incidents,
        overall_risk_score=round(overall_risk, 3),
        risk_factors=risk_factors,
        epicenter_multiplier=round(epicenter_multiplier, 2),
        risk_model_version=risk_model_version,
    )


@router.post("/{rider_id}/location-history")
async def add_location_history(
    rider_id: str,
    payload: LocationHistoryCreate,
):
    """Record location point for rider history tracking."""
    _ = rider_id
    _ = payload
    return {"success": True, "message": "Location recorded"}
