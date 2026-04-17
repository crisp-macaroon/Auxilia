"""
Claims API Router
Endpoints for insurance claims processing
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.models.database import Claim, Policy, Rider, Zone
from app.models.schemas import (
    ClaimCreate, ClaimResponse, ClaimWithDetails,
    ClaimStatus, TriggerType, PolicyStatus, APIResponse
)
from app.agents.trigger_agent import trigger_agent
from app.agents.fraud_agent import fraud_agent
from app.agents.payout_agent import payout_agent
from app.core.security import get_optional_admin, require_admin

router = APIRouter(prefix="/claims", tags=["Claims"])

# Trigger thresholds
TRIGGER_THRESHOLDS = {
    TriggerType.RAIN: settings.RAIN_THRESHOLD_MM,
    TriggerType.TRAFFIC: settings.CONGESTION_THRESHOLD,
    TriggerType.SURGE: settings.SURGE_THRESHOLD,
    TriggerType.ROAD_DISRUPTION: settings.INCIDENT_THRESHOLD
}


@router.get("/public-payout-log")
async def get_public_payout_log(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Public, anonymized payout log for transparency and trust."""
    result = await db.execute(
        select(Claim)
        .where(Claim.status == ClaimStatus.PAID.value)
        .order_by(Claim.processed_at.desc(), Claim.created_at.desc())
        .limit(limit)
    )
    paid_claims = result.scalars().all()

    rows = []
    for claim in paid_claims:
        rider_result = await db.execute(select(Rider).where(Rider.id == claim.rider_id))
        rider = rider_result.scalar_one_or_none()

        policy_result = await db.execute(select(Policy).where(Policy.id == claim.policy_id))
        policy = policy_result.scalar_one_or_none()

        zone_name = None
        if policy:
            zone_result = await db.execute(select(Zone).where(Zone.id == policy.zone_id))
            zone = zone_result.scalar_one_or_none()
            zone_name = zone.name if zone else policy.zone_id

        masked_rider = "Rider"
        if rider and rider.name:
            masked_rider = f"{rider.name[0]}***"

        rows.append({
            "claim_id": claim.id,
            "rider": masked_rider,
            "trigger_type": claim.trigger_type,
            "trigger_value": round(float(claim.trigger_value or 0.0), 2),
            "threshold": round(float(claim.threshold or 0.0), 2),
            "payout_amount": round(float(claim.amount or 0.0), 2),
            "zone": zone_name,
            "tx_hash": claim.tx_hash,
            "processed_at": (claim.processed_at or claim.created_at).isoformat(),
        })

    return {
        "count": len(rows),
        "payouts": rows,
        "note": "Anonymized parametric payout events with verifiable transaction hash.",
    }


@router.post("/", response_model=ClaimResponse)
async def create_claim(
    claim: ClaimCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a new insurance claim.
    Automatically validates trigger and processes payout if eligible.
    """
    # Get policy
    policy_result = await db.execute(
        select(Policy).where(Policy.id == claim.policy_id)
    )
    policy = policy_result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if policy.status != PolicyStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Policy is not active")
    
    if policy.end_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Policy has expired")
    
    # Get rider
    rider_result = await db.execute(
        select(Rider).where(Rider.id == policy.rider_id)
    )
    rider = rider_result.scalar_one_or_none()
    
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    
    # Get current trigger value from trigger agent
    trigger_signal = trigger_agent.get_latest_signal(policy.zone_id)
    
    if not trigger_signal:
        # Check triggers now
        trigger_signal = await trigger_agent.check_zone(policy.zone_id)
    
    # Find the relevant trigger
    threshold = TRIGGER_THRESHOLDS.get(claim.trigger_type, 0)
    trigger_value = 0.0
    
    for t in trigger_signal.get("triggers", []):
        if t.trigger_type == claim.trigger_type:
            trigger_value = t.current_value
            break
    
    # Create claim record
    claim_id = str(uuid.uuid4())
    
    db_claim = Claim(
        id=claim_id,
        policy_id=policy.id,
        rider_id=rider.id,
        trigger_type=claim.trigger_type.value,
        trigger_value=trigger_value,
        threshold=threshold,
        amount=0.0,  # Will be set after validation
        status=ClaimStatus.PENDING.value,
        fraud_score=0.0,
        ai_decision=None,
        tx_hash=None,
        created_at=datetime.utcnow(),
        processed_at=None
    )
    
    db.add(db_claim)
    await db.commit()
    await db.refresh(db_claim)
    
    # Process claim in background
    background_tasks.add_task(
        process_claim_async,
        claim_id=claim_id,
        policy=policy,
        rider=rider,
        trigger_type=claim.trigger_type,
        trigger_value=trigger_value,
        threshold=threshold
    )
    
    return db_claim


async def process_claim_async(
    claim_id: str,
    policy,
    rider,
    trigger_type: TriggerType,
    trigger_value: float,
    threshold: float
):
    """Background task to process claim with AI agents."""
    from app.core.database import async_session_maker
    
    async with async_session_maker() as db:
        try:
            # Get claim
            result = await db.execute(
                select(Claim).where(Claim.id == claim_id)
            )
            claim = result.scalar_one()
            
            claim.status = ClaimStatus.PROCESSING.value
            await db.commit()
            
            # Get claim history for fraud check
            history_result = await db.execute(
                select(Claim).where(Claim.rider_id == rider.id)
            )
            claims = history_result.scalars().all()
            
            claim_history = [
                {
                    "id": c.id,
                    "zone_id": policy.zone_id,
                    "trigger_type": c.trigger_type,
                    "status": c.status,
                    "amount": c.amount,
                    "created_at": c.created_at
                }
                for c in claims if c.id != claim_id
            ]
            
            # Run fraud validation
            fraud_assessment = await fraud_agent.validate_claim(
                claim_id=claim_id,
                rider_id=rider.id,
                zone_id=policy.zone_id,
                trigger_type=trigger_type.value,
                rider_location=(rider.latitude, rider.longitude) if rider.latitude else None,
                trigger_timestamp=datetime.utcnow(),
                claim_history=claim_history
            )
            
            claim.fraud_score = fraud_assessment.fraud_score
            
            # Check if claim should be rejected
            if fraud_assessment.verification_status == "rejected":
                claim.status = ClaimStatus.REJECTED.value
                claim.ai_decision = f"Rejected: {', '.join(fraud_assessment.risk_flags)}"
                claim.processed_at = datetime.utcnow()
                await db.commit()
                return
            
            # Check if trigger is valid
            if trigger_value < threshold:
                claim.status = ClaimStatus.REJECTED.value
                claim.ai_decision = f"Trigger not met: {trigger_value} < {threshold}"
                claim.processed_at = datetime.utcnow()
                await db.commit()
                return
            
            # Get zone for name
            zone_result = await db.execute(
                select(Zone).where(Zone.id == policy.zone_id)
            )
            zone = zone_result.scalar_one_or_none()
            zone_name = zone.name if zone else policy.zone_id
            
            # Process payout
            payout = await payout_agent.process_payout(
                claim_id=claim_id,
                policy_id=policy.id,
                rider_id=rider.id,
                rider_phone=rider.phone,
                rider_name=rider.name,
                zone_name=zone_name,
                trigger_type=trigger_type.value,
                trigger_value=trigger_value,
                threshold=threshold,
                coverage_amount=policy.coverage,
                zone_earning_index=float(getattr(zone, "earning_index", 1.0) or 1.0),
                rider_earning_profile={
                    "earning_model": getattr(rider, "earning_model", "per_delivery"),
                    "avg_order_value": getattr(rider, "avg_order_value", 120.0),
                    "avg_hourly_income": getattr(rider, "avg_hourly_income", 180.0),
                    "avg_daily_orders": getattr(rider, "avg_daily_orders", 12),
                    "avg_km_rate": getattr(rider, "avg_km_rate", 18.0),
                },
                fraud_score=fraud_assessment.fraud_score,
                policy_valid=True
            )
            
            if payout.approved:
                claim.status = ClaimStatus.PAID.value
                claim.amount = payout.payout_amount
                claim.tx_hash = payout.blockchain_tx_hash
                claim.ai_decision = payout.decision_reason
            else:
                claim.status = ClaimStatus.REJECTED.value
                claim.ai_decision = payout.decision_reason
            
            claim.processed_at = datetime.utcnow()
            await db.commit()
            
        except Exception as e:
            import logging
            logging.error(f"Claim processing error: {e}")
            
            # Mark claim as needing manual review
            claim.status = ClaimStatus.PENDING.value
            claim.ai_decision = f"Error during processing: {str(e)}"
            await db.commit()


@router.get("/", response_model=List[ClaimResponse])
async def list_claims(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[ClaimStatus] = None,
    rider_id: Optional[str] = None,
    trigger_type: Optional[TriggerType] = None,
    db: AsyncSession = Depends(get_db),
    admin: Optional[dict] = Depends(get_optional_admin),
):
    """List all claims with optional filters."""
    if rider_id is None and admin is None:
        raise HTTPException(status_code=401, detail="Missing admin token")
    query = select(Claim)
    
    if status:
        query = query.where(Claim.status == status.value)
    if rider_id:
        query = query.where(Claim.rider_id == rider_id)
    if trigger_type:
        query = query.where(Claim.trigger_type == trigger_type.value)
    
    query = query.order_by(Claim.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get claim by ID."""
    result = await db.execute(
        select(Claim).where(Claim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    return claim


@router.get("/{claim_id}/details")
async def get_claim_details(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Get claim with full details including rider, policy, and zone."""
    result = await db.execute(
        select(Claim).where(Claim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Get related data
    policy_result = await db.execute(
        select(Policy).where(Policy.id == claim.policy_id)
    )
    policy = policy_result.scalar_one_or_none()
    
    rider_result = await db.execute(
        select(Rider).where(Rider.id == claim.rider_id)
    )
    rider = rider_result.scalar_one_or_none()
    
    zone = None
    if policy:
        zone_result = await db.execute(
            select(Zone).where(Zone.id == policy.zone_id)
        )
        zone = zone_result.scalar_one_or_none()
    
    # Get fraud assessment if available
    fraud_assessment = fraud_agent.get_cached_assessment(claim_id)
    payout_decision = await payout_agent.get_payout_status(claim_id)
    earning_context = None
    if rider or zone:
        earning_context = payout_agent.get_earning_exposure_details(
            zone_earning_index=float(getattr(zone, "earning_index", 1.0) or 1.0),
            rider_earning_profile={
                "earning_model": getattr(rider, "earning_model", "per_delivery") if rider else "per_delivery",
                "avg_order_value": getattr(rider, "avg_order_value", 120.0) if rider else 120.0,
                "avg_hourly_income": getattr(rider, "avg_hourly_income", 180.0) if rider else 180.0,
                "avg_daily_orders": getattr(rider, "avg_daily_orders", 12) if rider else 12,
                "avg_km_rate": getattr(rider, "avg_km_rate", 18.0) if rider else 18.0,
            },
        )
    
    return {
        "claim": claim,
        "policy": policy,
        "rider": rider,
        "zone": zone,
        "fraud_assessment": fraud_assessment.model_dump() if fraud_assessment else None,
        "payout_decision": payout_decision.model_dump() if payout_decision else None,
        "earning_context": earning_context,
    }


@router.post("/{claim_id}/approve")
async def approve_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Manually approve a pending claim."""
    result = await db.execute(
        select(Claim).where(Claim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    if claim.status not in [ClaimStatus.PENDING.value, ClaimStatus.PROCESSING.value]:
        raise HTTPException(status_code=400, detail="Claim cannot be approved")
    
    claim.status = ClaimStatus.APPROVED.value
    claim.ai_decision = "Manually approved"
    claim.processed_at = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True, "message": "Claim approved"}


@router.post("/{claim_id}/reject")
async def reject_claim(
    claim_id: str,
    reason: str = "Claim rejected by administrator",
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Manually reject a pending claim."""
    result = await db.execute(
        select(Claim).where(Claim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    if claim.status not in [ClaimStatus.PENDING.value, ClaimStatus.PROCESSING.value]:
        raise HTTPException(status_code=400, detail="Claim cannot be rejected")
    
    claim.status = ClaimStatus.REJECTED.value
    claim.ai_decision = reason
    claim.processed_at = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True, "message": "Claim rejected"}


@router.get("/stats/overview")
async def get_claim_stats(
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Get overall claim statistics."""
    total = await db.execute(select(func.count(Claim.id)))
    pending = await db.execute(
        select(func.count(Claim.id)).where(Claim.status == ClaimStatus.PENDING.value)
    )
    approved = await db.execute(
        select(func.count(Claim.id)).where(Claim.status == ClaimStatus.APPROVED.value)
    )
    paid = await db.execute(
        select(func.count(Claim.id)).where(Claim.status == ClaimStatus.PAID.value)
    )
    rejected = await db.execute(
        select(func.count(Claim.id)).where(Claim.status == ClaimStatus.REJECTED.value)
    )
    total_payout = await db.execute(
        select(func.sum(Claim.amount)).where(
            or_(
                Claim.status == ClaimStatus.APPROVED.value,
                Claim.status == ClaimStatus.PAID.value,
            )
        )
    )
    avg_fraud_score = await db.execute(select(func.avg(Claim.fraud_score)))
    
    # Claims by trigger type
    rain_claims = await db.execute(
        select(func.count(Claim.id)).where(Claim.trigger_type == TriggerType.RAIN.value)
    )
    traffic_claims = await db.execute(
        select(func.count(Claim.id)).where(Claim.trigger_type == TriggerType.TRAFFIC.value)
    )
    
    return {
        "total_claims": total.scalar() or 0,
        "pending_claims": pending.scalar() or 0,
        "approved_claims": (approved.scalar() or 0) + (paid.scalar() or 0),
        "rejected_claims": rejected.scalar() or 0,
        "total_payout": round(total_payout.scalar() or 0, 2),
        "average_fraud_score": round(avg_fraud_score.scalar() or 0, 3),
        "by_trigger_type": {
            "rain": rain_claims.scalar() or 0,
            "traffic": traffic_claims.scalar() or 0
        }
    }
