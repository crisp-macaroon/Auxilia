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
    PersonaType.QCOMMERCE: 99.0,      # Rs 99/week baseline
    PersonaType.FOOD_DELIVERY: 99.0   # Rs 99/week baseline
}

COVERAGE_AMOUNTS = {
    PersonaType.QCOMMERCE: 2000.0,    # Rs 2000 weekly coverage for Q-Commerce
    PersonaType.FOOD_DELIVERY: 1500.0 # Rs 1500 weekly coverage for food delivery
}

BASE_COVERAGE_HOURS = {
    PersonaType.QCOMMERCE: 60,
    PersonaType.FOOD_DELIVERY: 48,
}


def _calculate_weekly_adjustment(
    base_premium: float,
    zone_factor: float,
    risk_score: float,
    weather_risk: float,
    traffic_risk: float,
    incident_risk: float,
) -> tuple[float, str]:
    zone_adjustment = round((zone_factor - 1.0) * 10)

    if risk_score <= 0.30:
        risk_adjustment = -2
    elif risk_score <= 0.45:
        risk_adjustment = 0
    elif risk_score <= 0.60:
        risk_adjustment = 2
    elif risk_score <= 0.75:
        risk_adjustment = 4
    else:
        risk_adjustment = 6

    event_adjustment = 0
    reasons: list[str] = []
    if weather_risk >= 0.55:
        event_adjustment += 2
        reasons.append("predictive weather pressure")
    if traffic_risk >= 0.60:
        event_adjustment += 1
        reasons.append("hyper-local congestion")
    if incident_risk >= 0.50:
        event_adjustment += 1
        reasons.append("delivery corridor disruption")

    weekly_adjustment = max(-4, min(8, zone_adjustment + risk_adjustment + event_adjustment))
    if weekly_adjustment < 0:
        note = f"Rs {abs(weekly_adjustment)} weekly discount for lower-risk operating conditions"
    elif weekly_adjustment > 0:
        note = f"Rs {weekly_adjustment} weekly uplift for elevated hyper-local disruption risk"
    else:
        note = "Base weekly premium retained for balanced local risk"

    if reasons and weekly_adjustment > 0:
        note = f"{note} ({', '.join(reasons)})"

    return float(weekly_adjustment), note


def _derive_live_zone_factor(
    static_zone_factor: float,
    combined_zone_risk: float,
) -> float:
    """
    Blend persisted zone pricing with current local zone conditions.
    Keeps pricing responsive without letting short-lived spikes fully override
    the configured base zone profile.
    """
    live_zone_factor = 0.9 + (combined_zone_risk * 0.5)
    blended_zone_factor = (static_zone_factor * 0.55) + (live_zone_factor * 0.45)
    return round(max(0.8, min(1.75, blended_zone_factor)), 3)


def _recommended_coverage_hours(
    persona: PersonaType,
    weather_risk: float,
    incident_risk: float,
    final_risk_score: float,
) -> int:
    extra_hours = 0
    if weather_risk >= 0.60:
        extra_hours += 6
    if incident_risk >= 0.50 or final_risk_score >= 0.65:
        extra_hours += 6
    return BASE_COVERAGE_HOURS.get(persona, 48) + extra_hours


def _resolve_duration_factor(duration_days: int) -> float:
    if duration_days >= 28:
        return 0.85
    if duration_days >= 21:
        return 0.90
    if duration_days >= 14:
        return 0.95
    if duration_days >= 7:
        return 1.0
    return 1.15


@router.get("/trust-rules/public")
async def get_public_trust_rules():
    """Public trust rules to show parametric payout logic before purchase."""
    return {
        "parametric_only": True,
        "message": "Payouts are trigger-based. No document-heavy manual claim review for basic eligibility.",
        "trigger_rules": [
            {
                "trigger_type": "rain",
                "threshold": settings.RAIN_THRESHOLD_MM,
                "base_payout": settings.RAIN_PAYOUT,
            },
            {
                "trigger_type": "traffic",
                "threshold": settings.CONGESTION_THRESHOLD,
                "base_payout": settings.TRAFFIC_PAYOUT,
            },
            {
                "trigger_type": "road_disruption",
                "threshold": settings.INCIDENT_THRESHOLD,
                "base_payout": settings.ROAD_DISRUPTION_PAYOUT,
            },
            {
                "trigger_type": "surge",
                "threshold": settings.SURGE_THRESHOLD,
                "base_payout": settings.SURGE_PAYOUT,
            },
        ],
        "payout_severity_model": {
            "just_above_threshold": "partial payout",
            "far_above_threshold": "higher payout",
        },
    }


@router.get("/offer-window/public")
async def get_public_offer_window(
    zone_id: str,
):
    """Timing-aware nudge window for high-risk shift activation."""
    zone_assessment = await risk_agent.assess_zone_risk(zone_id)

    combined = float(zone_assessment.get("combined_risk", 0.0))
    weather = float(zone_assessment.get("weather_risk", 0.0))
    traffic = float(zone_assessment.get("traffic_risk", 0.0))
    incident = float(zone_assessment.get("incident_risk", 0.0))

    high_risk_window = (
        combined >= 0.58
        or weather >= 0.55
        or traffic >= 0.60
        or incident >= 0.50
    )
    rain_probability = int(max(5, min(95, round(weather * 100))))

    if high_risk_window:
        nudge = (
            f"Rain probability {rain_probability}%. Estimated disruption risk is elevated. "
            f"Best activation window: next 24-48 hours."
        )
    else:
        nudge = (
            f"Current risk is moderate. Rain probability {rain_probability}%. "
            f"You can activate now or wait for a higher-risk window."
        )

    return {
        "zone_id": zone_id,
        "high_risk_window": high_risk_window,
        "nudge": nudge,
        "risk_level": zone_assessment.get("risk_level", "medium"),
        "combined_risk": round(combined, 3),
        "rain_probability_percent": rain_probability,
        "event_window_seconds": zone_assessment.get("event_window_seconds", 300),
        "assessed_at": zone_assessment.get("assessed_at"),
    }


@router.get("/quote-preview/public")
async def get_quote_preview(
    zone_id: str,
    persona: PersonaType,
    duration_days: int = 7,
):
    """Public quote preview with expected-value and regret-protection hints."""
    base_premium = BASE_PREMIUM.get(persona, 99.0)
    base_coverage = COVERAGE_AMOUNTS.get(persona, 3000.0)

    zone_assessment = await risk_agent.assess_zone_risk(zone_id)
    combined = float(zone_assessment.get("combined_risk", 0.0))

    dynamic_weekly = max(65.0, min(249.0, round(base_premium + (combined - 0.45) * 22, 2)))
    duration_factor = _resolve_duration_factor(duration_days)
    final_premium = round(dynamic_weekly * duration_factor * max(1, duration_days / 7), 2)

    estimated_income_at_risk = round(base_coverage * min(0.82, (0.28 + combined * 0.62)), 2)
    expected_payout = round(estimated_income_at_risk * min(0.9, (0.32 + combined * 0.58)), 2)
    loyalty_points = int(max(10, round(dynamic_weekly * 0.45)))

    return {
        "zone_id": zone_id,
        "persona": persona,
        "duration_days": duration_days,
        "weekly_premium": dynamic_weekly,
        "final_premium": final_premium,
        "coverage": base_coverage,
        "risk_level": zone_assessment.get("risk_level", "medium"),
        "expected_value": {
            "estimated_income_at_risk": estimated_income_at_risk,
            "expected_payout": expected_payout,
            "note": "Expected value is estimated from local trigger risk, not guaranteed payout.",
        },
        "regret_protection": {
            "loyalty_points_if_no_trigger": loyalty_points,
            "reward_type": "loyalty_points",
            "note": "If no trigger activates this week, loyalty points are credited for consistent coverage.",
        },
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


@router.get("/alerts/pricing")
async def get_pricing_alerts(
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Surface admin-facing alerts for weekly premium shifts driven by local risk."""
    zones_result = await db.execute(select(Zone).where(Zone.is_active == True))
    zones = zones_result.scalars().all()

    alerts = []
    for zone in zones:
        assessment = await risk_agent.assess_zone_risk(zone.id)
        weekly_adjustment, pricing_note = _calculate_weekly_adjustment(
            base_premium=BASE_PREMIUM[PersonaType.QCOMMERCE],
            zone_factor=zone.base_premium_factor,
            risk_score=float(assessment.get("combined_risk", 0.0)),
            weather_risk=float(assessment.get("weather_risk", 0.0)),
            traffic_risk=float(assessment.get("traffic_risk", 0.0)),
            incident_risk=float(assessment.get("incident_risk", 0.0)),
        )
        if weekly_adjustment == 0:
            continue

        alerts.append({
            "zone_id": zone.id,
            "zone_name": zone.name,
            "city": zone.city,
            "weekly_adjustment": weekly_adjustment,
            "suggested_weekly_premium": BASE_PREMIUM[PersonaType.QCOMMERCE] + weekly_adjustment,
            "recommended_coverage_hours": _recommended_coverage_hours(
                PersonaType.QCOMMERCE,
                float(assessment.get("weather_risk", 0.0)),
                float(assessment.get("incident_risk", 0.0)),
                float(assessment.get("combined_risk", 0.0)),
            ),
            "risk_level": assessment.get("risk_level", "medium"),
            "risk_scope": assessment.get("scope", "zone_event"),
            "event_window_seconds": assessment.get("event_window_seconds"),
            "pricing_note": pricing_note,
            "assessed_at": assessment.get("assessed_at"),
        })

    alerts.sort(key=lambda item: abs(item["weekly_adjustment"]), reverse=True)
    return {"alerts": alerts[:8], "count": len(alerts)}


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
    static_zone_factor = zone.base_premium_factor if zone else 1.0

    zone_assessment = await risk_agent.assess_zone_risk(zone_id)
    combined_zone_risk = float(zone_assessment.get("combined_risk", 0.0))
    zone_factor = _derive_live_zone_factor(static_zone_factor, combined_zone_risk)
    
    # Get rider risk assessment
    rider_result = await db.execute(
        select(Rider).where(Rider.id == rider_id)
    )
    rider = rider_result.scalar_one_or_none()
    
    assessment = None
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
    
    duration_factor = _resolve_duration_factor(duration_days)
    
    if assessment is not None:
        weekly_adjustment, pricing_note = _calculate_weekly_adjustment(
            base_premium=base_premium,
            zone_factor=zone_factor,
            risk_score=assessment.final_risk_score,
            weather_risk=assessment.weather_risk,
            traffic_risk=assessment.traffic_risk,
            incident_risk=assessment.incident_risk,
        )
        recommended_coverage_hours = _recommended_coverage_hours(
            persona=persona,
            weather_risk=assessment.weather_risk,
            incident_risk=assessment.incident_risk,
            final_risk_score=assessment.final_risk_score,
        )
    else:
        weekly_adjustment = 0.0
        pricing_note = "Base weekly premium retained for balanced local risk"
        recommended_coverage_hours = BASE_COVERAGE_HOURS.get(persona, 48)

    premium_model_version = "fallback-v1"
    premium_multiplier = max(0.75, min(1.85, zone_factor * risk_factor))
    if assessment is not None:
        try:
            from app.services.ml_service import premium_ml_service

            now = datetime.utcnow()
            premium_multiplier = premium_ml_service.predict_weekly_multiplier(
                zone_id=zone_id,
                zone_factor=zone_factor,
                zone_base_risk=assessment.base_risk_score,
                risk_score=assessment.final_risk_score,
                weather_risk=assessment.weather_risk,
                traffic_risk=assessment.traffic_risk,
                incident_risk=assessment.incident_risk,
                historical_risk=assessment.historical_risk,
                persona=persona,
                month=now.month,
                hour=now.hour,
            )
            premium_model_version = premium_ml_service.model_version
        except Exception:
            premium_model_version = "fallback-v1"

    weekly_premium = max(65.0, min(249.0, round(base_premium * premium_multiplier + weekly_adjustment, 2)))

    # Calculate final premium with ML multiplier and duration factor
    weeks = max(1, duration_days / 7)
    final_premium = weekly_premium * duration_factor * weeks
    final_premium = round(final_premium, 2)
    
    return {
        "base_premium": base_premium,
        "zone_factor": zone_factor,
        "persona_factor": 1.0,  # Already in base
        "risk_factor": risk_factor,
        "premium_multiplier": round(premium_multiplier, 3),
        "premium_model_version": premium_model_version,
        "weekly_adjustment": weekly_adjustment,
        "duration_factor": duration_factor,
        "duration_days": duration_days,
        "final_premium": final_premium,
        "coverage": base_coverage,
        "recommended_coverage_hours": recommended_coverage_hours,
        "pricing_note": pricing_note,
        "expected_value": {
            "estimated_income_at_risk": round(base_coverage * min(0.82, 0.26 + (combined_zone_risk * 0.62)), 2),
            "expected_payout": round(base_coverage * min(0.72, 0.16 + (combined_zone_risk * 0.48)), 2),
            "note": "Estimated from hyper-local trigger risk and zone conditions.",
        },
        "regret_protection": {
            "loyalty_points_if_no_trigger": int(max(10, round(weekly_premium * 0.45))),
            "reward_type": "loyalty_points",
            "note": "Loyalty points accrue when no trigger event occurs in coverage window.",
        },
        "breakdown": {
            "base": base_premium,
            "static_zone_factor": round(static_zone_factor, 3),
            "live_zone_risk": round(combined_zone_risk, 3),
            "live_zone_premium_multiplier": round(zone_assessment.get("premium_multiplier", 1.0), 3),
            "zone_risk_level": zone_assessment.get("risk_level", "medium"),
            "risk_scope": zone_assessment.get("scope", "zone_event"),
            "event_window_seconds": zone_assessment.get("event_window_seconds"),
            "weekly_adjustment": weekly_adjustment,
            "weekly_premium": round(weekly_premium, 2),
            "risk_score": round(assessment.final_risk_score, 3) if assessment else 0.0,
            "weather_risk": round(assessment.weather_risk, 3) if assessment else 0.0,
            "traffic_risk": round(assessment.traffic_risk, 3) if assessment else 0.0,
            "incident_risk": round(assessment.incident_risk, 3) if assessment else 0.0,
            "risk_model_version": assessment.ml_model_version if assessment else None,
            "premium_model_version": premium_model_version,
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
