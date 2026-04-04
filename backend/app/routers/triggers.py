"""
Triggers API Router
Endpoints for parametric trigger monitoring
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, cast
from datetime import datetime
import uuid
import math

from app.core.database import get_db
from app.models.database import TriggerEvent, Zone, Policy
from app.models.schemas import (
    TriggerStatus, TriggerEventCreate, TriggerEventResponse,
    TriggerType, PolicyStatus
)
from app.core.config import settings
from app.agents.trigger_agent import trigger_agent, ZONE_CONFIG
from app.services.weather_service import weather_service
from app.services.traffic_service import traffic_service
from app.services.news_service import news_service
from app.services.surge_service import surge_service
from app.services.location_service import location_service
from app.core.security import require_admin

router = APIRouter(prefix="/triggers", tags=["Triggers"])


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in kilometers."""
    earth_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_km * c


async def _resolve_zone_context(
    db: AsyncSession,
    zone_id: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> dict:
    """
    Resolve usable zone context from:
    1) explicit zone_id in DB or configured zones
    2) nearest DB zone from lat/lon
    3) reverse-geocoded dynamic location from lat/lon
    """
    if zone_id:
        db_zone_result = await db.execute(select(Zone).where(Zone.id == zone_id))
        db_zone = db_zone_result.scalar_one_or_none()
        if db_zone:
            return {
                "zone_id": db_zone.id,
                "zone_name": db_zone.name,
                "city": db_zone.city,
                "lat": db_zone.latitude,
                "lon": db_zone.longitude,
                "resolved_from": "database_zone_id",
            }

        if zone_id in ZONE_CONFIG:
            zone = ZONE_CONFIG[zone_id]
            return {
                "zone_id": zone_id,
                "zone_name": zone["name"],
                "city": zone["city"],
                "lat": zone["lat"],
                "lon": zone["lon"],
                "resolved_from": "configured_zone_id",
            }

    if lat is None or lon is None:
        zones_result = await db.execute(select(Zone).where(Zone.is_active == True))
        zones = zones_result.scalars().all()
        if zones:
            fallback = zones[0]
            return {
                "zone_id": fallback.id,
                "zone_name": fallback.name,
                "city": fallback.city,
                "lat": fallback.latitude,
                "lon": fallback.longitude,
                "resolved_from": "fallback_first_database_zone",
            }

        if ZONE_CONFIG:
            fallback_id = next(iter(ZONE_CONFIG.keys()))
            fallback_zone = ZONE_CONFIG[fallback_id]
            return {
                "zone_id": fallback_id,
                "zone_name": fallback_zone["name"],
                "city": fallback_zone["city"],
                "lat": fallback_zone["lat"],
                "lon": fallback_zone["lon"],
                "resolved_from": "fallback_first_configured_zone",
            }

        raise HTTPException(status_code=404, detail="No zones available")

    zones_result = await db.execute(select(Zone).where(Zone.is_active == True))
    zones = zones_result.scalars().all()
    if zones:
        nearest = min(
            zones,
            key=lambda z: _distance_km(
                lat,
                lon,
                cast(float, z.latitude),
                cast(float, z.longitude),
            ),
        )
        return {
            "zone_id": nearest.id,
            "zone_name": nearest.name,
            "city": nearest.city,
            "lat": nearest.latitude,
            "lon": nearest.longitude,
            "resolved_from": "nearest_database_zone",
        }

    reverse = await location_service.reverse_geocode(lat, lon)
    city = reverse.city if reverse and reverse.city else "Unknown"
    name = reverse.suburb if reverse and reverse.suburb else city
    return {
        "zone_id": zone_id or f"dynamic-{lat:.3f}-{lon:.3f}",
        "zone_name": name,
        "city": city,
        "lat": lat,
        "lon": lon,
        "resolved_from": "dynamic_reverse_geocode",
    }


async def _build_trigger_snapshot(zone_ctx: dict) -> dict:
    """Build trigger status snapshot using resolved zone context."""
    zone_id = zone_ctx["zone_id"]
    zone_name = zone_ctx["zone_name"]
    city = zone_ctx["city"]
    lat = zone_ctx["lat"]
    lon = zone_ctx["lon"]

    triggers: List[TriggerStatus] = []

    weather = await weather_service.get_current_weather(lat, lon)
    if weather:
        rain_value = max(weather.rain_1h, weather.rain_3h / 3)
        triggers.append(
            TriggerStatus(
                zone_id=zone_id,
                zone_name=zone_name,
                trigger_type=TriggerType.RAIN,
                current_value=round(rain_value, 2),
                threshold=settings.RAIN_THRESHOLD_MM,
                is_active=(
                    weather.rain_1h >= settings.RAIN_THRESHOLD_MM
                    or weather.rain_3h >= settings.RAIN_THRESHOLD_MM
                ),
                affected_policies=0,
                last_updated=datetime.utcnow(),
                source="OpenWeatherMap",
            )
        )

    traffic = await traffic_service.get_traffic_flow(lat, lon)
    if traffic:
        triggers.append(
            TriggerStatus(
                zone_id=zone_id,
                zone_name=zone_name,
                trigger_type=TriggerType.TRAFFIC,
                current_value=round(traffic.congestion_level, 1),
                threshold=settings.CONGESTION_THRESHOLD,
                is_active=traffic.congestion_level >= settings.CONGESTION_THRESHOLD,
                affected_policies=0,
                last_updated=datetime.utcnow(),
                source="TomTom",
            )
        )

    incidents = await news_service.search_incidents(city, "road disruption", hours_back=6)
    relevant_count = len([i for i in incidents if i.is_trigger_relevant])
    triggers.append(
        TriggerStatus(
            zone_id=zone_id,
            zone_name=zone_name,
            trigger_type=TriggerType.ROAD_DISRUPTION,
            current_value=float(relevant_count),
            threshold=float(settings.INCIDENT_THRESHOLD),
            is_active=relevant_count >= settings.INCIDENT_THRESHOLD,
            affected_policies=0,
            last_updated=datetime.utcnow(),
            source="NewsAPI",
        )
    )

    surge = await surge_service.get_current_surge(zone_id, lat, lon)
    if surge:
        triggers.append(
            TriggerStatus(
                zone_id=zone_id,
                zone_name=zone_name,
                trigger_type=TriggerType.SURGE,
                current_value=round(surge.surge_multiplier, 2),
                threshold=settings.SURGE_THRESHOLD,
                is_active=surge.surge_multiplier < settings.SURGE_THRESHOLD,
                affected_policies=0,
                last_updated=datetime.utcnow(),
                source="SurgeService",
            )
        )

    active_count = len([t for t in triggers if t.is_active])
    return {
        "zone_id": zone_id,
        "zone_name": zone_name,
        "city": city,
        "triggers": triggers,
        "active_count": active_count,
        "checked_at": datetime.utcnow().isoformat(),
        "resolved_from": zone_ctx["resolved_from"],
    }


@router.get("/status")
async def get_trigger_status(_admin: dict = Depends(require_admin)):
    """
    Get current trigger status for all zones.
    Returns active triggers with real-time data.
    """
    signals = trigger_agent.get_all_signals()
    
    if not signals:
        # Check all zones if no cached data
        await trigger_agent.check_all_zones()
        signals = trigger_agent.get_all_signals()
    
    return {
        "zones": signals,
        "total_zones": len(ZONE_CONFIG),
        "zones_with_triggers": len([z for z in signals.values() if z.get("active_count", 0) > 0]),
        "checked_at": datetime.utcnow().isoformat()
    }


@router.get("/status/{zone_id}")
async def get_zone_trigger_status(
    zone_id: str,
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get trigger status for a zone, with optional lat/lon fallback."""
    zone_ctx = await _resolve_zone_context(db=db, zone_id=zone_id, lat=lat, lon=lon)
    return await _build_trigger_snapshot(zone_ctx)


@router.post("/check")
async def check_all_triggers(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger a check of all zones.
    Creates trigger events for any active triggers.
    """
    results = await trigger_agent.check_all_zones()
    
    # Record any active triggers
    for zone_id, signal in results.items():
        for trigger in signal.get("triggers", []):
            if trigger.is_active:
                # Create trigger event record
                event = TriggerEvent(
                    id=str(uuid.uuid4()),
                    zone_id=zone_id,
                    trigger_type=trigger.trigger_type.value,
                    value=trigger.current_value,
                    threshold=trigger.threshold,
                    is_active=True,
                    source=trigger.source,
                    raw_data=None,
                    created_at=datetime.utcnow()
                )
                db.add(event)
    
    await db.commit()
    
    # Count active triggers
    active_zones = [z for z, s in results.items() if s.get("active_count", 0) > 0]
    total_triggers = sum(s.get("active_count", 0) for s in results.values())
    
    return {
        "success": True,
        "zones_checked": len(results),
        "zones_with_triggers": len(active_zones),
        "total_active_triggers": total_triggers,
        "active_zones": active_zones,
        "checked_at": datetime.utcnow().isoformat()
    }


@router.get("/active")
async def get_active_triggers(_admin: dict = Depends(require_admin)):
    """Get all currently active triggers across all zones."""
    active = trigger_agent.get_active_triggers()
    
    all_active = []
    for zone_id, triggers in active.items():
        for t in triggers:
            if t.is_active:
                all_active.append({
                    "zone_id": zone_id,
                    "zone_name": t.zone_name,
                    "trigger_type": t.trigger_type.value,
                    "current_value": t.current_value,
                    "threshold": t.threshold,
                    "source": t.source,
                    "last_updated": t.last_updated.isoformat()
                })
    
    return {
        "active_triggers": all_active,
        "count": len(all_active)
    }


@router.get("/history")
async def get_trigger_history(
    zone_id: Optional[str] = None,
    trigger_type: Optional[TriggerType] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Get historical trigger events."""
    query = select(TriggerEvent)
    
    if zone_id:
        query = query.where(TriggerEvent.zone_id == zone_id)
    if trigger_type:
        query = query.where(TriggerEvent.trigger_type == trigger_type.value)
    
    query = query.order_by(TriggerEvent.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return {"events": events, "count": len(events)}


@router.get("/weather/{zone_id}")
async def get_zone_weather(
    zone_id: str,
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed weather data for a zone, with optional lat/lon fallback."""
    zone = await _resolve_zone_context(db=db, zone_id=zone_id, lat=lat, lon=lon)
    
    # Get current weather
    current = await weather_service.get_current_weather(zone["lat"], zone["lon"])
    
    if not current:
        raise HTTPException(status_code=503, detail="Weather service unavailable")
    
    # Get forecast
    forecast = await weather_service.get_forecast(zone["lat"], zone["lon"], hours=24)
    
    return {
        "zone_id": zone_id,
        "zone_name": zone["zone_name"],
        "city": zone["city"],
        "resolved_from": zone["resolved_from"],
        "current": current.model_dump() if current else None,
        "forecast": forecast,
        "rain_trigger_active": weather_service.is_rain_trigger_active(current) if current else False
    }


@router.get("/traffic/{zone_id}")
async def get_zone_traffic(
    zone_id: str,
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed traffic data for a zone, with optional lat/lon fallback."""
    zone = await _resolve_zone_context(db=db, zone_id=zone_id, lat=lat, lon=lon)
    
    # Get traffic flow
    traffic = await traffic_service.get_traffic_flow(zone["lat"], zone["lon"])
    
    if not traffic:
        raise HTTPException(status_code=503, detail="Traffic service unavailable")
    
    # Get incidents in area (5km bounding box)
    bbox = (
        zone["lon"] - 0.05,  # ~5km west
        zone["lat"] - 0.05,  # ~5km south
        zone["lon"] + 0.05,  # ~5km east
        zone["lat"] + 0.05   # ~5km north
    )
    incidents = await traffic_service.get_traffic_incidents(bbox)
    
    return {
        "zone_id": zone_id,
        "zone_name": zone["zone_name"],
        "resolved_from": zone["resolved_from"],
        "traffic": traffic.model_dump(),
        "incidents": incidents,
        "congestion_trigger_active": traffic_service.is_congestion_trigger_active(traffic)
    }


@router.get("/news/{zone_id}")
async def get_zone_news(
    zone_id: str,
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get incident news for a zone, with optional lat/lon fallback."""
    zone = await _resolve_zone_context(db=db, zone_id=zone_id, lat=lat, lon=lon)
    
    # Get incidents from news
    incidents = await news_service.search_incidents(zone["city"], hours_back=24)
    
    return {
        "zone_id": zone_id,
        "zone_name": zone["zone_name"],
        "city": zone["city"],
        "resolved_from": zone["resolved_from"],
        "incidents": [i.model_dump() for i in incidents],
        "incident_count": len(incidents),
        "relevant_count": len([i for i in incidents if i.is_trigger_relevant])
    }


@router.get("/surge/{zone_id}")
async def get_zone_surge(
    zone_id: str,
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get surge/demand data for a zone, with optional lat/lon fallback."""
    zone = await _resolve_zone_context(db=db, zone_id=zone_id, lat=lat, lon=lon)
    
    # Get current surge
    surge = await surge_service.get_current_surge(zone_id, zone["lat"], zone["lon"])
    
    # Get forecast
    forecast = await surge_service.get_surge_forecast(zone_id, hours_ahead=6)
    
    return {
        "zone_id": zone_id,
        "zone_name": zone["zone_name"],
        "resolved_from": zone["resolved_from"],
        "current": surge.model_dump(),
        "forecast": forecast,
        "low_demand_trigger": surge_service.is_surge_trigger_active(surge)
    }


@router.get("/affected-policies/{zone_id}")
async def get_affected_policies(
    zone_id: str,
    trigger_type: Optional[TriggerType] = None,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Get count of policies affected by triggers in a zone."""
    query = select(func.count(Policy.id)).where(
        Policy.zone_id == zone_id,
        Policy.status == PolicyStatus.ACTIVE.value
    )
    
    result = await db.execute(query)
    count = result.scalar() or 0
    
    return {
        "zone_id": zone_id,
        "active_policies": count,
        "potential_claims": count  # All active policies could claim
    }


@router.get("/thresholds")
async def get_trigger_thresholds():
    """Get current trigger thresholds configuration."""
    from app.core.config import settings
    
    return {
        "rain": {
            "threshold": settings.RAIN_THRESHOLD_MM,
            "unit": "mm/hour",
            "description": "Rain intensity threshold"
        },
        "traffic": {
            "threshold": settings.CONGESTION_THRESHOLD,
            "unit": "0-10 scale",
            "description": "Traffic congestion level"
        },
        "surge": {
            "threshold": settings.SURGE_THRESHOLD,
            "unit": "multiplier",
            "description": "Minimum surge for income protection (below = trigger)"
        },
        "incident": {
            "threshold": settings.INCIDENT_THRESHOLD,
            "unit": "count",
            "description": "Number of incidents in zone"
        }
    }
