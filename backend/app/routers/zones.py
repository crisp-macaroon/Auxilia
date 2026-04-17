"""
Zones API Router
Endpoints for zone management
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.database import Zone, Policy, Claim
from app.models.schemas import ZoneCreate, ZoneResponse, ZoneWithTriggers, PolicyStatus, InsurerZoneCreate
from app.agents.trigger_agent import trigger_agent, ZONE_CONFIG
from app.agents.risk_agent import risk_agent
from app.services.location_service import location_service

router = APIRouter(prefix="/zones", tags=["Zones"])


CITY_EARNING_INDEX = {
    "mumbai": 1.18,
    "delhi": 1.16,
    "gurgaon": 1.14,
    "bengaluru": 1.12,
    "bangalore": 1.12,
    "hyderabad": 1.04,
    "pune": 1.0,
    "chennai": 0.98,
    "kochi": 0.92,
    "thiruvananthapuram": 0.9,
    "kerala": 0.9,
}

ZONE_EARNING_INDEX = {
    "MUM-AND": 1.22,
    "MUM-BAN": 1.24,
    "MUM-POW": 1.15,
    "DEL-CON": 1.2,
    "DEL-GUR": 1.18,
    "BLR-KOR": 1.14,
    "BLR-IND": 1.15,
    "BLR-WHT": 1.08,
    "BLR-HSR": 1.1,
    "HYD-HIB": 1.06,
    "PUN-KOT": 1.01,
    "CHN-ANN": 0.99,
}


def _default_earning_index(zone_id: str, city: str) -> float:
    if zone_id in ZONE_EARNING_INDEX:
        return ZONE_EARNING_INDEX[zone_id]
    return CITY_EARNING_INDEX.get((city or "").strip().lower(), 1.0)


@router.post("/", response_model=ZoneResponse)
async def create_zone(
    zone: ZoneCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new coverage zone."""
    # Check if zone ID exists
    existing = await db.execute(
        select(Zone).where(Zone.id == zone.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Zone ID already exists")
    
    db_zone = Zone(
        id=zone.id,
        name=zone.name,
        city=zone.city,
        state=zone.state,
        country=zone.country,
        latitude=zone.latitude,
        longitude=zone.longitude,
        radius_km=zone.radius_km,
        risk_level=zone.risk_level,
        base_premium_factor=zone.base_premium_factor,
        earning_index=zone.earning_index if zone.earning_index else _default_earning_index(zone.id, zone.city),
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.add(db_zone)
    await db.commit()
    await db.refresh(db_zone)
    
    return db_zone


@router.post("/dynamic", response_model=ZoneResponse)
async def create_dynamic_insurer_zone(
    payload: InsurerZoneCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a dynamic insurer-defined zone from map coordinates.
    Reverse-geocodes location with OSM/Nominatim and stores a normalized zone.
    """
    reverse = await location_service.reverse_geocode(payload.latitude, payload.longitude)

    zone_name = payload.name.strip()
    zone_city = payload.city or (reverse.city if reverse else "")
    zone_state = payload.state or (reverse.state if reverse else "")
    zone_country = payload.country or (reverse.country if reverse else "IN")

    normalized = f"{zone_city}-{zone_name}-{str(payload.latitude)[:6]}-{str(payload.longitude)[:6]}"
    zone_id = normalized.lower().replace(" ", "-").replace("/", "-")

    existing = await db.execute(select(Zone).where(Zone.id == zone_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Dynamic zone already exists")

    db_zone = Zone(
        id=zone_id,
        name=zone_name,
        city=zone_city,
        state=zone_state,
        country=zone_country,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_km=payload.radius_km,
        risk_level=payload.risk_level,
        base_premium_factor=1.0,
        earning_index=payload.earning_index or _default_earning_index(zone_id, zone_city),
        is_active=True,
        created_at=datetime.utcnow(),
    )

    db.add(db_zone)
    await db.commit()
    await db.refresh(db_zone)
    return db_zone


@router.get("/", response_model=List[ZoneResponse])
async def list_zones(
    city: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all zones with optional filters."""
    query = select(Zone)
    
    if city:
        query = query.where(Zone.city == city)
    if is_active is not None:
        query = query.where(Zone.is_active == is_active)
    
    query = query.order_by(Zone.city, Zone.name)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/configured")
async def get_configured_zones():
    """Get all pre-configured zones from trigger agent."""
    return {
        "zones": [
            {
                "id": zone_id,
                "name": zone["name"],
                "city": zone["city"],
                "latitude": zone["lat"],
                "longitude": zone["lon"]
            }
            for zone_id, zone in ZONE_CONFIG.items()
        ],
        "total": len(ZONE_CONFIG)
    }


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get zone by ID."""
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id)
    )
    zone = result.scalar_one_or_none()
    
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return zone


@router.get("/{zone_id}/status")
async def get_zone_status(
    zone_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive zone status including triggers and statistics."""
    # Check if zone is configured
    if zone_id not in ZONE_CONFIG:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone_config = ZONE_CONFIG[zone_id]
    
    # Get from database if exists
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id)
    )
    zone_db = result.scalar_one_or_none()
    
    # Get current triggers
    trigger_signal = await trigger_agent.check_zone(zone_id)
    
    # Get zone risk assessment
    risk_assessment = await risk_agent.assess_zone_risk(zone_id)
    
    # Get policy count
    policy_count = await db.execute(
        select(func.count(Policy.id)).where(
            Policy.zone_id == zone_id,
            Policy.status == PolicyStatus.ACTIVE.value
        )
    )
    
    # Get claim count
    claim_count = await db.execute(
        select(func.count(Claim.id)).where(
            Claim.rider_id.in_(
                select(Policy.rider_id).where(Policy.zone_id == zone_id)
            )
        )
    )
    
    return {
        "zone_id": zone_id,
        "name": zone_config["name"],
        "city": zone_config["city"],
        "coordinates": {
            "latitude": zone_config["lat"],
            "longitude": zone_config["lon"]
        },
        "database_record": zone_db is not None,
        "triggers": trigger_signal,
        "risk": risk_assessment,
        "statistics": {
            "active_policies": policy_count.scalar() or 0,
            "total_claims": claim_count.scalar() or 0
        }
    }


@router.get("/{zone_id}/risk")
async def get_zone_risk(zone_id: str):
    """Get detailed risk assessment for a zone."""
    if zone_id not in ZONE_CONFIG:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return await risk_agent.assess_zone_risk(zone_id)


@router.get("/{zone_id}/policies")
async def get_zone_policies(
    zone_id: str,
    status: Optional[PolicyStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all policies in a zone."""
    query = select(Policy).where(Policy.zone_id == zone_id)
    
    if status:
        query = query.where(Policy.status == status.value)
    
    query = query.order_by(Policy.created_at.desc())
    
    result = await db.execute(query)
    policies = result.scalars().all()
    
    return {
        "zone_id": zone_id,
        "policies": policies,
        "count": len(policies)
    }


@router.patch("/{zone_id}")
async def update_zone(
    zone_id: str,
    risk_level: Optional[str] = None,
    base_premium_factor: Optional[float] = None,
    earning_index: Optional[float] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update zone settings."""
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id)
    )
    zone = result.scalar_one_or_none()
    
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    if risk_level is not None:
        zone.risk_level = risk_level
    if base_premium_factor is not None:
        zone.base_premium_factor = base_premium_factor
    if earning_index is not None:
        zone.earning_index = earning_index
    if is_active is not None:
        zone.is_active = is_active
    
    await db.commit()
    await db.refresh(zone)
    
    return zone


@router.get("/cities/list")
async def list_cities(db: AsyncSession = Depends(get_db)):
    """Get list of unique cities with zones."""
    # From configured zones
    configured_cities = list(set(z["city"] for z in ZONE_CONFIG.values()))
    
    # From database
    result = await db.execute(select(Zone.city).distinct())
    db_cities = [row[0] for row in result.all()]
    
    all_cities = sorted(set(configured_cities + db_cities))
    
    return {"cities": all_cities}


@router.post("/seed")
async def seed_zones(db: AsyncSession = Depends(get_db)):
    """Seed database with pre-configured zones."""
    created = 0
    
    for zone_id, zone_config in ZONE_CONFIG.items():
        # Check if exists
        existing = await db.execute(
            select(Zone).where(Zone.id == zone_id)
        )
        if existing.scalar_one_or_none():
            continue
        
        # Create zone
        zone = Zone(
            id=zone_id,
            name=zone_config["name"],
            city=zone_config["city"],
            state="",
            country="IN",
            latitude=zone_config["lat"],
            longitude=zone_config["lon"],
            radius_km=5.0,
            risk_level="medium",
            base_premium_factor=1.0,
            earning_index=_default_earning_index(zone_id, zone_config["city"]),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(zone)
        created += 1
    
    await db.commit()
    
    return {
        "success": True,
        "zones_created": created,
        "total_configured": len(ZONE_CONFIG)
    }
