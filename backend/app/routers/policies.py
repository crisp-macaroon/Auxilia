"""
Policies API Router
Endpoints for insurance policy management
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.models.database import Policy, Rider, Zone
from app.models.schemas import (
    PolicyCreate, PolicyResponse, PolicyWithRider,
    PolicyStatus, PersonaType, PremiumCalculation, APIResponse
)
from app.agents.risk_agent import risk_agent
from app.core.security import get_optional_admin, require_admin
import hashlib

router = APIRouter(prefix="/policies", tags=["Policies"])


def generate_policy_hash(policy_id: str, rider_id: str, zone_id: str, premium: float) -> str:
    """
    Generate a simulated blockchain transaction hash for a policy.
    In production, this would be a real on-chain transaction.
    """
    data = f"policy:{policy_id}:{rider_id}:{zone_id}:{premium}:{datetime.utcnow().isoformat()}"
    return "0x" + hashlib.sha256(data.encode()).hexdigest()

# Premium configuration (WEEKLY basis as per golden rules)
BASE_PREMIUM = {
    PersonaType.QCOMMERCE: 99.0,      # Rs 99/week for Q-Commerce (Zepto/Blinkit)
    PersonaType.FOOD_DELIVERY: 79.0   # Rs 79/week for food delivery (secondary)
}

COVERAGE_AMOUNTS = {
    PersonaType.QCOMMERCE: 2000.0,    # Rs 2000 weekly coverage for Q-Commerce
    PersonaType.FOOD_DELIVERY: 1500.0 # Rs 1500 weekly coverage for food delivery
}


@router.post("/", response_model=PolicyResponse)
async def create_policy(
    policy: PolicyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new insurance policy for a rider."""
    # Verify rider exists
    rider_result = await db.execute(
        select(Rider).where(Rider.id == policy.rider_id)
    )
    rider = rider_result.scalar_one_or_none()
    
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # Check for existing active policy
    existing = await db.execute(
        select(Policy).where(
            Policy.rider_id == policy.rider_id,
            Policy.status == PolicyStatus.ACTIVE.value,
            Policy.end_date > datetime.utcnow()
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Rider already has an active policy")
    
    # Calculate premium with risk assessment
    premium_calc = await calculate_premium(
        rider_id=policy.rider_id,
        zone_id=policy.zone_id,
        persona=policy.persona,
        duration_days=policy.duration_days,
        db=db
    )
    
    now = datetime.utcnow()
    policy_id = str(uuid.uuid4())
    
    # Generate blockchain tx_hash immediately for demo
    tx_hash = generate_policy_hash(
        policy_id=policy_id,
        rider_id=policy.rider_id,
        zone_id=policy.zone_id,
        premium=premium_calc["final_premium"]
    )
    
    db_policy = Policy(
        id=policy_id,
        rider_id=policy.rider_id,
        zone_id=policy.zone_id,
        persona=policy.persona.value,
        premium=premium_calc["final_premium"],
        coverage=premium_calc["coverage"],
        start_date=now,
        end_date=now + timedelta(days=policy.duration_days),
        status=PolicyStatus.ACTIVE.value,
        tx_hash=tx_hash,
        created_at=now
    )
    
    db.add(db_policy)
    await db.commit()
    await db.refresh(db_policy)
    
    return db_policy


@router.get("/", response_model=List[PolicyResponse])
async def list_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[PolicyStatus] = None,
    zone_id: Optional[str] = None,
    rider_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: Optional[dict] = Depends(get_optional_admin),
):
    """List all policies with optional filters."""
    if rider_id is None and admin is None:
        raise HTTPException(status_code=401, detail="Missing admin token")
    query = select(Policy)
    
    if status:
        query = query.where(Policy.status == status.value)
    if zone_id:
        query = query.where(Policy.zone_id == zone_id)
    if rider_id:
        query = query.where(Policy.rider_id == rider_id)
    
    query = query.order_by(Policy.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get policy by ID."""
    result = await db.execute(
        select(Policy).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return policy


@router.get("/{policy_id}/details")
async def get_policy_details(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Get policy with rider and zone details."""
    result = await db.execute(
        select(Policy).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Get rider
    rider_result = await db.execute(
        select(Rider).where(Rider.id == policy.rider_id)
    )
    rider = rider_result.scalar_one_or_none()
    
    # Get zone
    zone_result = await db.execute(
        select(Zone).where(Zone.id == policy.zone_id)
    )
    zone = zone_result.scalar_one_or_none()
    
    return {
        "policy": policy,
        "rider": rider,
        "zone": zone,
        "days_remaining": max(0, (policy.end_date - datetime.utcnow()).days),
        "is_active": policy.status == PolicyStatus.ACTIVE.value and policy.end_date > datetime.utcnow()
    }


@router.post("/{policy_id}/cancel")
async def cancel_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel an active policy."""
    result = await db.execute(
        select(Policy).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if policy.status != PolicyStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Policy is not active")
    
    policy.status = PolicyStatus.CANCELLED.value
    
    await db.commit()
    
    return {"success": True, "message": "Policy cancelled"}


@router.post("/{policy_id}/renew")
async def renew_policy(
    policy_id: str,
    duration_days: int = 7,  # Weekly renewal by default
    db: AsyncSession = Depends(get_db)
):
    """Renew an expiring/expired policy."""
    result = await db.execute(
        select(Policy).where(Policy.id == policy_id)
    )
    old_policy = result.scalar_one_or_none()
    
    if not old_policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Create new policy based on old one
    premium_calc = await calculate_premium(
        rider_id=old_policy.rider_id,
        zone_id=old_policy.zone_id,
        persona=PersonaType(old_policy.persona),
        duration_days=duration_days,
        db=db
    )
    
    now = datetime.utcnow()
    start_date = max(now, old_policy.end_date)  # Start after old policy ends
    new_policy_id = str(uuid.uuid4())
    
    # Generate blockchain tx_hash immediately for demo
    tx_hash = generate_policy_hash(
        policy_id=new_policy_id,
        rider_id=old_policy.rider_id,
        zone_id=old_policy.zone_id,
        premium=premium_calc["final_premium"]
    )
    
    new_policy = Policy(
        id=new_policy_id,
        rider_id=old_policy.rider_id,
        zone_id=old_policy.zone_id,
        persona=old_policy.persona,
        premium=premium_calc["final_premium"],
        coverage=premium_calc["coverage"],
        start_date=start_date,
        end_date=start_date + timedelta(days=duration_days),
        status=PolicyStatus.ACTIVE.value,
        tx_hash=tx_hash,
        created_at=now
    )
    
    # Mark old policy as expired
    old_policy.status = PolicyStatus.EXPIRED.value
    
    db.add(new_policy)
    await db.commit()
    await db.refresh(new_policy)
    
    return {
        "success": True,
        "old_policy_id": policy_id,
        "new_policy": new_policy
    }


@router.post("/calculate-premium")
async def calculate_premium_endpoint(
    rider_id: str,
    zone_id: str,
    persona: PersonaType,
    duration_days: int = 7,  # Weekly by default
    db: AsyncSession = Depends(get_db)
):
    """Calculate premium for a potential policy."""
    return await calculate_premium(rider_id, zone_id, persona, duration_days, db)


async def calculate_premium(
    rider_id: str,
    zone_id: str,
    persona: PersonaType,
    duration_days: int,
    db: AsyncSession
) -> dict:
    """Calculate premium with risk-based pricing."""
    # Get base premium and coverage
    base_premium = BASE_PREMIUM.get(persona, 99.0)
    base_coverage = COVERAGE_AMOUNTS.get(persona, 3000.0)
    
    # Get zone risk factor
    zone_result = await db.execute(
        select(Zone).where(Zone.id == zone_id)
    )
    zone = zone_result.scalar_one_or_none()
    zone_factor = zone.base_premium_factor if zone else 1.0
    
    # Get rider risk assessment
    rider_result = await db.execute(
        select(Rider).where(Rider.id == rider_id)
    )
    rider = rider_result.scalar_one_or_none()
    
    if rider:
        assessment = await risk_agent.assess_rider_risk(
            rider_id=rider_id,
            zone_id=zone_id,
            persona=persona,
            lat=rider.latitude,
            lon=rider.longitude,
            rider_profile={
                "age_band": rider.age_band,
                "vehicle_type": rider.vehicle_type,
                "shift_type": rider.shift_type,
                "tenure_months": rider.tenure_months,
            },
        )
        risk_factor = risk_agent.calculate_premium_multiplier(assessment.final_risk_score)
    else:
        risk_factor = 1.0
    
    # Duration factor (weekly model - longer commitments get discount)
    # Standard is 7 days (1 week), discounts for multi-week
    if duration_days >= 28:  # 4+ weeks
        duration_factor = 0.85
    elif duration_days >= 21:  # 3 weeks
        duration_factor = 0.9
    elif duration_days >= 14:  # 2 weeks
        duration_factor = 0.95
    elif duration_days >= 7:  # 1 week (standard)
        duration_factor = 1.0
    else:
        duration_factor = 1.15  # Less than a week costs more
    
    # Calculate final premium (base is per-week, scale by weeks)
    weeks = max(1, duration_days / 7)
    final_premium = base_premium * zone_factor * risk_factor * duration_factor * weeks
    final_premium = round(final_premium, 2)
    
    return {
        "base_premium": base_premium,
        "zone_factor": zone_factor,
        "persona_factor": 1.0,  # Already in base
        "risk_factor": risk_factor,
        "duration_factor": duration_factor,
        "duration_days": duration_days,
        "final_premium": final_premium,
        "coverage": base_coverage,
        "breakdown": {
            "base": base_premium,
            "after_zone": round(base_premium * zone_factor, 2),
            "after_risk": round(base_premium * zone_factor * risk_factor, 2),
            "after_duration": final_premium
        }
    }


@router.get("/stats/overview")
async def get_policy_stats(
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Get overall policy statistics."""
    total = await db.execute(select(func.count(Policy.id)))
    active = await db.execute(
        select(func.count(Policy.id)).where(
            Policy.status == PolicyStatus.ACTIVE.value,
            Policy.end_date > datetime.utcnow(),
        )
    )
    total_premium = await db.execute(select(func.sum(Policy.premium)))
    total_coverage = await db.execute(select(func.sum(Policy.coverage)))
    
    return {
        "total_policies": total.scalar() or 0,
        "active_policies": active.scalar() or 0,
        "total_premium_collected": round(total_premium.scalar() or 0, 2),
        "total_coverage_liability": round(total_coverage.scalar() or 0, 2)
    }
