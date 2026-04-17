"""
Riders API Router
Endpoints for rider management
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.database import Rider, Policy, Claim
from app.models.database import DeliveryCheckInEvent
from app.models.schemas import (
    RiderCreate, RiderUpdate, RiderResponse,
    PersonaType, RiderStatus, APIResponse,
    DeliveryCheckInRequest, DeliveryCheckInResponse,
    DeliveryHistoryItem,
)
from app.agents.risk_agent import risk_agent
from app.services.location_service import location_service
from app.models.database import Zone
from app.core.config import settings
from app.core.security import require_admin
from app.routers.zones import _default_earning_index

router = APIRouter(prefix="/riders", tags=["Riders"])


def _build_rider_profile(rider: Rider | RiderCreate | RiderUpdate) -> dict:
    return {
        "age_band": getattr(rider, "age_band", None),
        "vehicle_type": getattr(rider, "vehicle_type", None),
        "shift_type": getattr(rider, "shift_type", None),
        "tenure_months": getattr(rider, "tenure_months", 0) or 0,
        "earning_model": getattr(rider, "earning_model", "per_delivery") or "per_delivery",
        "avg_order_value": getattr(rider, "avg_order_value", 120.0) or 120.0,
        "avg_hourly_income": getattr(rider, "avg_hourly_income", 180.0) or 180.0,
        "avg_daily_orders": getattr(rider, "avg_daily_orders", 12) or 12,
        "avg_km_rate": getattr(rider, "avg_km_rate", 18.0) or 18.0,
    }


@router.post("/", response_model=RiderResponse)
async def create_rider(
    rider: RiderCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new rider for insurance coverage."""
    # Check if phone already exists
    existing = await db.execute(
        select(Rider).where(Rider.phone == rider.phone)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Calculate initial risk score
    risk_assessment = await risk_agent.assess_rider_risk(
        rider_id="new",
        zone_id=rider.zone_id,
        persona=rider.persona,
        lat=rider.latitude if rider.latitude is not None else None,
        lon=rider.longitude if rider.longitude is not None else None,
        claim_history=[],
        rider_profile=_build_rider_profile(rider),
    )
    
    db_rider = Rider(
        id=str(uuid.uuid4()),
        name=rider.name,
        phone=rider.phone,
        email=rider.email,
        persona=rider.persona.value,
        zone_id=rider.zone_id,
        age_band=rider.age_band,
        vehicle_type=rider.vehicle_type,
        shift_type=rider.shift_type,
        tenure_months=rider.tenure_months,
        earning_model=rider.earning_model,
        avg_order_value=rider.avg_order_value,
        avg_hourly_income=rider.avg_hourly_income,
        avg_daily_orders=rider.avg_daily_orders,
        avg_km_rate=rider.avg_km_rate,
        latitude=rider.latitude,
        longitude=rider.longitude,
        risk_score=risk_assessment.final_risk_score,
        status=RiderStatus.ACTIVE.value,
        created_at=datetime.utcnow()
    )
    
    db.add(db_rider)
    await db.commit()
    await db.refresh(db_rider)
    
    return db_rider


@router.get("/", response_model=List[RiderResponse])
async def list_riders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[RiderStatus] = None,
    zone_id: Optional[str] = None,
    persona: Optional[PersonaType] = None,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """List all riders with optional filters."""
    query = select(Rider)
    
    if status:
        query = query.where(Rider.status == status.value)
    if zone_id:
        query = query.where(Rider.zone_id == zone_id)
    if persona:
        query = query.where(Rider.persona == persona.value)
    
    query = query.order_by(Rider.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{rider_id}", response_model=RiderResponse)
async def get_rider(
    rider_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get rider by ID."""
    result = await db.execute(
        select(Rider).where(Rider.id == rider_id)
    )
    rider = result.scalar_one_or_none()
    
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    return rider


@router.patch("/{rider_id}", response_model=RiderResponse)
async def update_rider(
    rider_id: str,
    update: RiderUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update rider information."""
    result = await db.execute(
        select(Rider).where(Rider.id == rider_id)
    )
    rider = result.scalar_one_or_none()
    
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    update_data = update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if value is not None:
            if hasattr(value, 'value'):
                setattr(rider, field, value.value)
            else:
                setattr(rider, field, value)
    
    # Recalculate risk if zone changed
    if update.zone_id:
        risk_assessment = await risk_agent.assess_rider_risk(
            rider_id=rider_id,
            zone_id=update.zone_id,
            persona=PersonaType(rider.persona),
            lat=rider.latitude,
            lon=rider.longitude,
            rider_profile=_build_rider_profile(rider),
        )
        rider.risk_score = risk_assessment.final_risk_score
    
    await db.commit()
    await db.refresh(rider)
    
    return rider


@router.get("/{rider_id}/risk")
async def get_rider_risk(
    rider_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed risk assessment for a rider."""
    result = await db.execute(
        select(Rider).where(Rider.id == rider_id)
    )
    rider = result.scalar_one_or_none()
    
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # Get claim history
    claims_result = await db.execute(
        select(Claim).where(Claim.rider_id == rider_id)
    )
    claims = claims_result.scalars().all()
    
    claim_history = [
        {
            "id": c.id,
            "status": c.status,
            "amount": c.amount,
            "created_at": c.created_at,
            "days_ago": (datetime.utcnow() - c.created_at).days
        }
        for c in claims
    ]
    
    assessment = await risk_agent.assess_rider_risk(
        rider_id=rider_id,
        zone_id=rider.zone_id,
        persona=PersonaType(rider.persona),
        lat=rider.latitude,
        lon=rider.longitude,
        claim_history=claim_history,
        rider_profile=_build_rider_profile(rider),
    )
    
    return {
        "rider_id": rider_id,
        "rider_name": rider.name,
        "assessment": assessment.model_dump()
    }


@router.get("/{rider_id}/policies")
async def get_rider_policies(
    rider_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all policies for a rider."""
    result = await db.execute(
        select(Policy).where(Policy.rider_id == rider_id).order_by(Policy.created_at.desc())
    )
    policies = result.scalars().all()
    
    return {"rider_id": rider_id, "policies": policies}


@router.get("/{rider_id}/claims")
async def get_rider_claims(
    rider_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all claims for a rider."""
    result = await db.execute(
        select(Claim).where(Claim.rider_id == rider_id).order_by(Claim.created_at.desc())
    )
    claims = result.scalars().all()
    
    return {"rider_id": rider_id, "claims": claims}


@router.post("/{rider_id}/update-location")
async def update_rider_location(
    rider_id: str,
    latitude: float,
    longitude: float,
    db: AsyncSession = Depends(get_db)
):
    """Update rider's current GPS location."""
    result = await db.execute(
        select(Rider).where(Rider.id == rider_id)
    )
    rider = result.scalar_one_or_none()
    
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    rider.latitude = latitude
    rider.longitude = longitude
    
    await db.commit()
    
    return {"success": True, "message": "Location updated"}


@router.post("/{rider_id}/delivery-checkin", response_model=DeliveryCheckInResponse)
async def delivery_checkin(
    rider_id: str,
    payload: DeliveryCheckInRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Rider submits delivery coordinates for insurance validity.
    Risk and eligibility are calculated against delivery location (not home/base rider zone).
    """
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    # Update rider live location if provided
    if payload.rider_latitude is not None and payload.rider_longitude is not None:
        rider.latitude = payload.rider_latitude
        rider.longitude = payload.rider_longitude

    # Find nearest active zone to delivery point
    zones_result = await db.execute(select(Zone).where(Zone.is_active == True))
    zones = zones_result.scalars().all()

    assigned_zone = None
    min_distance = None
    for zone in zones:
        distance = location_service._calculate_distance(
            payload.delivery_latitude,
            payload.delivery_longitude,
            zone.latitude,
            zone.longitude,
        )
        if min_distance is None or distance < min_distance:
            min_distance = distance
            assigned_zone = zone

    threshold_meters = settings.DELIVERY_ZONE_MAX_RADIUS_KM * 1000

    if not assigned_zone or (min_distance is not None and min_distance > threshold_meters):
        reverse = await location_service.reverse_geocode(
            payload.delivery_latitude,
            payload.delivery_longitude,
        )
        dynamic_name = (
            (reverse.suburb or reverse.road or reverse.city or "Dynamic Zone")
            if reverse
            else "Dynamic Zone"
        )
        dynamic_city = (reverse.city if reverse and reverse.city else "Unknown City")
        dynamic_state = (reverse.state if reverse and reverse.state else "")
        dynamic_country = (reverse.country if reverse and reverse.country else "IN")
        zone_id = f"auto-{dynamic_city}-{dynamic_name}-{str(payload.delivery_latitude)[:6]}-{str(payload.delivery_longitude)[:6]}"
        zone_id = zone_id.lower().replace(" ", "-").replace("/", "-")

        existing_dynamic = await db.execute(select(Zone).where(Zone.id == zone_id))
        assigned_zone = existing_dynamic.scalar_one_or_none()
        if not assigned_zone:
            assigned_zone = Zone(
                id=zone_id,
                name=dynamic_name,
                city=dynamic_city,
                state=dynamic_state,
                country=dynamic_country,
                latitude=payload.delivery_latitude,
                longitude=payload.delivery_longitude,
                radius_km=settings.DELIVERY_ZONE_MAX_RADIUS_KM,
                risk_level="medium",
                base_premium_factor=1.0,
                earning_index=_default_earning_index(zone_id, dynamic_city),
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(assigned_zone)
            await db.flush()

        min_distance = 0.0

    in_zone = (min_distance or 0.0) <= (assigned_zone.radius_km * 1000)

    reverse = await location_service.reverse_geocode(
        payload.delivery_latitude,
        payload.delivery_longitude,
    )
    city = reverse.city if reverse and reverse.city else assigned_zone.city
    state = reverse.state if reverse and reverse.state else (assigned_zone.state or "")
    country = reverse.country if reverse and reverse.country else (assigned_zone.country or "IN")

    assessment = await risk_agent.assess_delivery_risk(
        rider_id=rider.id,
        zone_id=assigned_zone.id,
        persona=PersonaType(rider.persona.value if hasattr(rider.persona, "value") else rider.persona),
        delivery_lat=payload.delivery_latitude,
        delivery_lon=payload.delivery_longitude,
        city=city,
        state=state,
        country=country,
        claim_history=[],
        rider_profile=_build_rider_profile(rider),
    )

    nearby_result = await db.execute(select(Rider).where(Rider.status == RiderStatus.ACTIVE.value))
    nearby_riders = nearby_result.scalars().all()
    in_radius_scores = []
    for nearby in nearby_riders:
        if nearby.latitude is None or nearby.longitude is None:
            continue
        distance = location_service._calculate_distance(
            assigned_zone.latitude,
            assigned_zone.longitude,
            nearby.latitude,
            nearby.longitude,
        )
        if distance <= assigned_zone.radius_km * 1000:
            in_radius_scores.append(float(nearby.risk_score or 0.0))

    if in_radius_scores:
        zone_risk = sum(in_radius_scores) / len(in_radius_scores)
        if zone_risk >= 0.7:
            assigned_zone.risk_level = "high"
            assigned_zone.base_premium_factor = 1.3
        elif zone_risk >= 0.4:
            assigned_zone.risk_level = "medium"
            assigned_zone.base_premium_factor = 1.0
        else:
            assigned_zone.risk_level = "low"
            assigned_zone.base_premium_factor = 0.85

    rider.zone_id = assigned_zone.id
    rider.risk_score = assessment.final_risk_score
    await db.commit()

    reason = (
        f"Delivery is within {assigned_zone.name} coverage zone"
        if in_zone
        else f"Delivery is outside {assigned_zone.name} radius"
    )

    checkin_event = DeliveryCheckInEvent(
        id=str(uuid.uuid4()),
        rider_id=rider.id,
        order_id=payload.order_id,
        assigned_zone_id=assigned_zone.id,
        assigned_zone_name=assigned_zone.name,
        delivery_latitude=payload.delivery_latitude,
        delivery_longitude=payload.delivery_longitude,
        rider_latitude=payload.rider_latitude,
        rider_longitude=payload.rider_longitude,
        distance_to_zone_center_meters=round(min_distance or 0.0, 2),
        is_delivery_in_coverage_zone=in_zone,
        eligibility_reason=reason,
        computed_risk_score=assessment.final_risk_score,
        weather_risk=assessment.weather_risk,
        traffic_risk=assessment.traffic_risk,
        incident_risk=assessment.incident_risk,
        assessed_at=assessment.assessed_at,
        created_at=datetime.utcnow(),
    )
    db.add(checkin_event)
    await db.commit()

    return DeliveryCheckInResponse(
        rider_id=rider.id,
        order_id=payload.order_id,
        assigned_zone_id=assigned_zone.id,
        assigned_zone_name=assigned_zone.name,
        distance_to_zone_center_meters=round(min_distance or 0.0, 2),
        is_delivery_in_coverage_zone=in_zone,
        eligibility_reason=reason,
        computed_risk_score=assessment.final_risk_score,
        weather_risk=assessment.weather_risk,
        traffic_risk=assessment.traffic_risk,
        incident_risk=assessment.incident_risk,
        assessed_at=assessment.assessed_at,
    )


@router.get("/{rider_id}/delivery-history", response_model=List[DeliveryHistoryItem])
async def get_delivery_history(
    rider_id: str,
    limit: int = Query(30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeliveryCheckInEvent)
        .where(DeliveryCheckInEvent.rider_id == rider_id)
        .order_by(DeliveryCheckInEvent.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/stats/overview")
async def get_rider_stats(
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Get overall rider statistics."""
    total = await db.execute(select(func.count(Rider.id)))
    active = await db.execute(
        select(func.count(Rider.id)).where(Rider.status == RiderStatus.ACTIVE.value)
    )
    avg_risk = await db.execute(select(func.avg(Rider.risk_score)))
    
    # Count by persona
    qcommerce = await db.execute(
        select(func.count(Rider.id)).where(Rider.persona == PersonaType.QCOMMERCE.value)
    )
    food_delivery = await db.execute(
        select(func.count(Rider.id)).where(Rider.persona == PersonaType.FOOD_DELIVERY.value)
    )
    
    return {
        "total_riders": total.scalar() or 0,
        "active_riders": active.scalar() or 0,
        "average_risk_score": round(avg_risk.scalar() or 0, 3),
        "by_persona": {
            "qcommerce": qcommerce.scalar() or 0,
            "food_delivery": food_delivery.scalar() or 0
        }
    }
