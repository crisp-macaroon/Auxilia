"""
Dashboard API Router
Endpoints for admin dashboard statistics and analytics
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, or_
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.models.database import Rider, Policy, Claim, Zone, TriggerEvent
from app.models.schemas import (
    DashboardStats,
    ClaimStatus,
    PolicyStatus,
    TriggerType,
    RiderStatus,
    ZoneHeatPoint,
)
from app.agents.trigger_agent import trigger_agent, ZONE_CONFIG
from app.core.security import require_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get main dashboard KPI statistics."""
    # Policy stats
    total_policies = await db.execute(select(func.count(Policy.id)))
    active_policies = await db.execute(
        select(func.count(Policy.id)).where(
            Policy.status == PolicyStatus.ACTIVE.value,
            Policy.end_date > datetime.utcnow(),
        )
    )
    
    # Claim stats
    total_claims = await db.execute(select(func.count(Claim.id)))
    pending_claims = await db.execute(
        select(func.count(Claim.id)).where(Claim.status == ClaimStatus.PENDING.value)
    )
    
    # Financial stats
    total_premium = await db.execute(select(func.sum(Policy.premium)))
    total_payouts = await db.execute(
        select(func.sum(Claim.amount)).where(
            or_(
                Claim.status == ClaimStatus.APPROVED.value,
                Claim.status == ClaimStatus.PAID.value,
            )
        )
    )
    
    # Rider stats
    active_riders = await db.execute(
        select(func.count(Rider.id)).where(Rider.status == RiderStatus.ACTIVE.value)
    )
    avg_risk = await db.execute(select(func.avg(Rider.risk_score)))
    
    # Active triggers
    all_signals = trigger_agent.get_all_signals()
    active_trigger_count = sum(
        s.get("active_count", 0) for s in all_signals.values()
    )
    
    # Calculate loss ratio
    premium = total_premium.scalar() or 0
    payouts = total_payouts.scalar() or 0
    loss_ratio = (payouts / premium * 100) if premium > 0 else 0
    
    return DashboardStats(
        total_policies=total_policies.scalar() or 0,
        active_policies=active_policies.scalar() or 0,
        total_claims=total_claims.scalar() or 0,
        pending_claims=pending_claims.scalar() or 0,
        total_premium_collected=round(premium, 2),
        total_claims_paid=round(payouts, 2),
        active_riders=active_riders.scalar() or 0,
        avg_risk_score=round(avg_risk.scalar() or 0, 3),
        active_triggers=active_trigger_count,
        loss_ratio=round(loss_ratio, 2)
    )


@router.get("/claims-chart")
async def get_claims_chart_data(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get claims data for chart visualization."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Get claims grouped by date
    result = await db.execute(
        select(
            func.date(Claim.created_at).label("date"),
            func.count(Claim.id).label("total"),
            func.sum(
                case((Claim.status == ClaimStatus.APPROVED.value, 1), else_=0)
            ).label("approved"),
            func.sum(
                case((Claim.status == ClaimStatus.REJECTED.value, 1), else_=0)
            ).label("rejected")
        ).where(Claim.created_at >= cutoff)
        .group_by(func.date(Claim.created_at))
        .order_by(func.date(Claim.created_at))
    )
    
    data = []
    for row in result.all():
        date_value = row.date.isoformat() if hasattr(row.date, "isoformat") else str(row.date) if row.date else None
        data.append({
            "date": date_value,
            "total": row.total or 0,
            "approved": row.approved or 0,
            "rejected": row.rejected or 0
        })
    
    return {"data": data, "days": days}


@router.get("/trigger-distribution")
async def get_trigger_distribution(
    db: AsyncSession = Depends(get_db)
):
    """Get distribution of claims by trigger type."""
    result = await db.execute(
        select(
            Claim.trigger_type,
            func.count(Claim.id).label("count"),
            func.sum(Claim.amount).label("total_payout")
        ).group_by(Claim.trigger_type)
    )
    
    distribution = []
    for row in result.all():
        distribution.append({
            "trigger_type": row.trigger_type,
            "count": row.count or 0,
            "total_payout": round(row.total_payout or 0, 2)
        })
    
    return {"distribution": distribution}


@router.get("/zone-stats")
async def get_zone_statistics(
    db: AsyncSession = Depends(get_db)
):
    """Get statistics by zone."""
    zones_data = []
    
    for zone_id, zone_config in ZONE_CONFIG.items():
        # Get policy count
        policies = await db.execute(
            select(func.count(Policy.id)).where(
                Policy.zone_id == zone_id,
                Policy.status == PolicyStatus.ACTIVE.value,
                Policy.end_date > datetime.utcnow(),
            )
        )
        
        # Get claim count
        claims = await db.execute(
            select(func.count(Claim.id), func.sum(Claim.amount)).where(
                Claim.rider_id.in_(
                    select(Policy.rider_id).where(Policy.zone_id == zone_id)
                )
            )
        )
        claim_row = claims.first()
        
        # Get trigger status
        signal = trigger_agent.get_latest_signal(zone_id)
        
        zones_data.append({
            "zone_id": zone_id,
            "name": zone_config["name"],
            "city": zone_config["city"],
            "active_policies": policies.scalar() or 0,
            "total_claims": claim_row[0] or 0 if claim_row else 0,
            "total_payouts": round(claim_row[1] or 0, 2) if claim_row else 0,
            "active_triggers": signal.get("active_count", 0) if signal else 0
        })
    
    return {"zones": zones_data}


@router.get("/recent-claims")
async def get_recent_claims(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get most recent claims with details."""
    result = await db.execute(
        select(Claim).order_by(Claim.created_at.desc()).limit(limit)
    )
    claims = result.scalars().all()
    
    # Enrich with rider names
    enriched = []
    for claim in claims:
        rider_result = await db.execute(
            select(Rider).where(Rider.id == claim.rider_id)
        )
        rider = rider_result.scalar_one_or_none()
        
        policy_result = await db.execute(
            select(Policy).where(Policy.id == claim.policy_id)
        )
        policy = policy_result.scalar_one_or_none()
        
        enriched.append({
            "id": claim.id,
            "rider_name": rider.name if rider else "Unknown",
            "zone_id": policy.zone_id if policy else "Unknown",
            "trigger_type": claim.trigger_type,
            "amount": claim.amount,
            "status": claim.status,
            "created_at": claim.created_at.isoformat()
        })
    
    return {"claims": enriched}


@router.get("/live-triggers")
async def get_live_triggers():
    """Get currently active triggers for live monitoring."""
    # Check all zones
    all_signals = trigger_agent.get_all_signals()
    
    live_triggers = []
    for zone_id, signal in all_signals.items():
        for trigger in signal.get("triggers", []):
            if trigger.is_active:
                live_triggers.append({
                    "zone_id": zone_id,
                    "zone_name": trigger.zone_name,
                    "trigger_type": trigger.trigger_type.value,
                    "current_value": trigger.current_value,
                    "threshold": trigger.threshold,
                    "source": trigger.source,
                    "severity": "high" if trigger.current_value > trigger.threshold * 1.5 else "medium",
                    "last_updated": trigger.last_updated.isoformat()
                })
    
    return {
        "triggers": live_triggers,
        "count": len(live_triggers),
        "checked_at": datetime.utcnow().isoformat()
    }


@router.get("/revenue-metrics")
async def get_revenue_metrics(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get revenue and payout metrics."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Premium collected
    premium = await db.execute(
        select(func.sum(Policy.premium)).where(Policy.created_at >= cutoff)
    )
    
    # Claims paid
    payouts = await db.execute(
            select(func.sum(Claim.amount)).where(
                Claim.status.in_([
                    ClaimStatus.APPROVED.value,
                    ClaimStatus.PAID.value,
                ]),
                Claim.processed_at >= cutoff
            )
        )
    
    # Average claim amount
    avg_claim = await db.execute(
            select(func.avg(Claim.amount)).where(
                Claim.status.in_([
                    ClaimStatus.APPROVED.value,
                    ClaimStatus.PAID.value,
                ])
            )
        )
    
    premium_val = premium.scalar() or 0
    payouts_val = payouts.scalar() or 0
    
    return {
        "period_days": days,
        "premium_collected": round(premium_val, 2),
        "claims_paid": round(payouts_val, 2),
        "net_revenue": round(premium_val - payouts_val, 2),
        "average_claim": round(avg_claim.scalar() or 0, 2),
        "loss_ratio": round((payouts_val / premium_val * 100) if premium_val > 0 else 0, 2)
    }


@router.get("/rider-personas")
async def get_rider_persona_breakdown(
    db: AsyncSession = Depends(get_db)
):
    """Get breakdown of riders by persona type."""
    result = await db.execute(
        select(
            Rider.persona,
            func.count(Rider.id).label("count"),
            func.avg(Rider.risk_score).label("avg_risk")
        ).group_by(Rider.persona)
    )
    
    breakdown = []
    for row in result.all():
        breakdown.append({
            "persona": row.persona,
            "count": row.count or 0,
            "average_risk_score": round(row.avg_risk or 0, 3)
        })
    
    return {"personas": breakdown}


@router.get("/alerts")
async def get_system_alerts(
    db: AsyncSession = Depends(get_db)
):
    """Get system alerts and notifications."""
    alerts = []
    
    # Check for pending claims
    pending = await db.execute(
        select(func.count(Claim.id)).where(Claim.status == ClaimStatus.PENDING.value)
    )
    pending_count = pending.scalar() or 0
    if pending_count > 0:
        alerts.append({
            "type": "warning",
            "title": "Pending Claims",
            "message": f"{pending_count} claims awaiting processing",
            "action": "/claims?status=pending"
        })
    
    # Check for expiring policies
    week_ahead = datetime.utcnow() + timedelta(days=7)
    expiring = await db.execute(
        select(func.count(Policy.id)).where(
            Policy.status == PolicyStatus.ACTIVE.value,
            Policy.end_date <= week_ahead,
            Policy.end_date > datetime.utcnow()
        )
    )
    expiring_count = expiring.scalar() or 0
    if expiring_count > 0:
        alerts.append({
            "type": "info",
            "title": "Expiring Policies",
            "message": f"{expiring_count} policies expiring this week",
            "action": "/policies?expiring=true"
        })
    
    # Check for active triggers
    signals = trigger_agent.get_all_signals()
    active_zones = [z for z, s in signals.items() if s.get("active_count", 0) > 0]
    if active_zones:
        alerts.append({
            "type": "critical",
            "title": "Active Triggers",
            "message": f"Triggers active in {len(active_zones)} zones",
            "action": "/triggers"
        })
    
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/zone-heatmap")
async def get_zone_heatmap(
    city: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Aggregated zone heat map data optimized for high rider counts.
    Heat score blends riders, policies, open claims, and risk score.
    """
    query = select(Zone)
    if city:
        query = query.where(Zone.city == city)

    zones_result = await db.execute(query)
    zones = zones_result.scalars().all()

    heat_points: list[ZoneHeatPoint] = []
    for zone in zones:
        active_riders_q = await db.execute(
            select(func.count(Rider.id)).where(
                Rider.zone_id == zone.id,
                Rider.status == RiderStatus.ACTIVE.value,
            )
        )
        active_policies_q = await db.execute(
            select(func.count(Policy.id)).where(
                Policy.zone_id == zone.id,
                Policy.status == PolicyStatus.ACTIVE.value,
                Policy.end_date > datetime.utcnow(),
            )
        )
        open_claims_q = await db.execute(
            select(func.count(Claim.id)).where(
                Claim.policy_id.in_(
                    select(Policy.id).where(Policy.zone_id == zone.id)
                ),
                Claim.status.in_([
                    ClaimStatus.PENDING.value,
                    ClaimStatus.PROCESSING.value,
                ])
            )
        )
        avg_risk_q = await db.execute(
            select(func.avg(Rider.risk_score)).where(Rider.zone_id == zone.id)
        )

        active_riders = active_riders_q.scalar() or 0
        active_policies = active_policies_q.scalar() or 0
        open_claims = open_claims_q.scalar() or 0
        avg_risk = float(avg_risk_q.scalar() or 0.0)

        density_component = min(1.0, (active_riders + active_policies) / 120.0)
        claim_component = min(1.0, open_claims / 20.0)
        risk_component = min(1.0, avg_risk)
        heat_score = round(
            density_component * 0.45 + claim_component * 0.2 + risk_component * 0.35,
            3,
        )

        heat_points.append(
            ZoneHeatPoint(
                zone_id=zone.id,
                zone_name=zone.name,
                city=zone.city,
                latitude=zone.latitude,
                longitude=zone.longitude,
                radius_km=zone.radius_km,
                active_riders=active_riders,
                active_policies=active_policies,
                open_claims=open_claims,
                avg_risk_score=round(avg_risk, 3),
                heat_score=heat_score,
            )
        )

    return {
        "city": city,
        "points": [point.model_dump() for point in heat_points],
        "count": len(heat_points),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/architecture")
async def get_architecture_and_pipeline():
    """Architecture + project flow used by admin for documentation view."""
    return {
        "architecture": {
            "frontend": ["Flutter Rider App", "Next.js Admin Dashboard"],
            "backend": ["FastAPI", "Async SQLAlchemy", "Agent Orchestrator"],
            "data": ["SQLite/PostgreSQL", "Tamper-evident claim log", "Policy/claim state"],
            "integrations": ["OpenWeatherMap", "TomTom", "NewsAPI + Gemini", "OpenStreetMap/Nominatim"],
            "blockchain": ["Claim ledger contract", "Tx hash evidence"],
        },
        "pipeline": [
            "Rider starts shift and location stream begins",
            "Rider enters delivery location coordinates for order check-in",
            "Backend maps delivery coordinates to nearest insurer-defined zone",
            "RiskAgent computes dynamic score (weather + traffic + zone/state/country incident pressure)",
            "TriggerAgent evaluates parametric conditions",
            "FraudAgent verifies delivery-zone eligibility and claim consistency",
            "PayoutAgent decides payout; approved claims get ledger hash",
            "Admin dashboard shows live zone heat map + metrics",
        ],
    }
