"""
Triggers API Router
Endpoints for parametric trigger monitoring
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.database import TriggerEvent, Zone, Policy
from app.models.schemas import (
    TriggerStatus, TriggerEventCreate, TriggerEventResponse,
    TriggerType, PolicyStatus
)
from app.agents.trigger_agent import trigger_agent, ZONE_CONFIG
from app.services.weather_service import weather_service
from app.services.traffic_service import traffic_service
from app.services.news_service import news_service
from app.services.surge_service import surge_service

router = APIRouter(prefix="/triggers", tags=["Triggers"])


@router.get("/status")
async def get_trigger_status():
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
async def get_zone_trigger_status(zone_id: str):
    """Get trigger status for a specific zone."""
    if zone_id not in ZONE_CONFIG:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Get fresh data
    signal = await trigger_agent.check_zone(zone_id)
    
    return signal


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
async def get_active_triggers():
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
    db: AsyncSession = Depends(get_db)
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
async def get_zone_weather(zone_id: str):
    """Get detailed weather data for a zone."""
    if zone_id not in ZONE_CONFIG:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone = ZONE_CONFIG[zone_id]
    
    # Get current weather
    current = await weather_service.get_current_weather(zone["lat"], zone["lon"])
    
    if not current:
        raise HTTPException(status_code=503, detail="Weather service unavailable")
    
    # Get forecast
    forecast = await weather_service.get_forecast(zone["lat"], zone["lon"], hours=24)
    
    return {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "city": zone["city"],
        "current": current.model_dump() if current else None,
        "forecast": forecast,
        "rain_trigger_active": weather_service.is_rain_trigger_active(current) if current else False
    }


@router.get("/traffic/{zone_id}")
async def get_zone_traffic(zone_id: str):
    """Get detailed traffic data for a zone."""
    if zone_id not in ZONE_CONFIG:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone = ZONE_CONFIG[zone_id]
    
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
        "zone_name": zone["name"],
        "traffic": traffic.model_dump(),
        "incidents": incidents,
        "congestion_trigger_active": traffic_service.is_congestion_trigger_active(traffic)
    }


@router.get("/news/{zone_id}")
async def get_zone_news(zone_id: str):
    """Get incident news for a zone."""
    if zone_id not in ZONE_CONFIG:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone = ZONE_CONFIG[zone_id]
    
    # Get incidents from news
    incidents = await news_service.search_incidents(zone["city"], hours_back=24)
    
    return {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "city": zone["city"],
        "incidents": [i.model_dump() for i in incidents],
        "incident_count": len(incidents),
        "relevant_count": len([i for i in incidents if i.is_trigger_relevant])
    }


@router.get("/surge/{zone_id}")
async def get_zone_surge(zone_id: str):
    """Get surge/demand data for a zone."""
    if zone_id not in ZONE_CONFIG:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone = ZONE_CONFIG[zone_id]
    
    # Get current surge
    surge = await surge_service.get_current_surge(zone_id, zone["lat"], zone["lon"])
    
    # Get forecast
    forecast = await surge_service.get_surge_forecast(zone_id, hours_ahead=6)
    
    return {
        "zone_id": zone_id,
        "zone_name": zone["name"],
        "current": surge.model_dump(),
        "forecast": forecast,
        "low_demand_trigger": surge_service.is_surge_trigger_active(surge)
    }


@router.get("/affected-policies/{zone_id}")
async def get_affected_policies(
    zone_id: str,
    trigger_type: Optional[TriggerType] = None,
    db: AsyncSession = Depends(get_db)
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
