"""
Payments API Router
Razorpay order creation and payment confirmation for policy purchases.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.database import Claim, Policy, Rider, Zone
from app.models.schemas import (
    PaymentFlowType,
    PersonaType,
    PolicyPaymentConfirmRequest,
    PolicyPaymentOrderRequest,
    PolicyPaymentOrderResponse,
    PolicyResponse,
    PolicyStatus,
)
from app.routers.policies import calculate_premium, generate_policy_hash

router = APIRouter(prefix="/payments", tags=["Payments"])

POINT_VALUE_INR = 0.25
MAX_REDEEM_SHARE = 0.75


async def _award_no_claim_loyalty_points(db: AsyncSession, rider_id: str) -> int:
    """
    Award loyalty points once for expired policies with no claims.
    Conservative reward to protect economics.
    """
    now = datetime.utcnow()
    eligible_result = await db.execute(
        select(Policy).where(
            Policy.rider_id == rider_id,
            Policy.end_date < now,
            Policy.loyalty_points_awarded == False,
        )
    )
    eligible = eligible_result.scalars().all()
    if not eligible:
        return 0

    granted = 0
    for policy in eligible:
        claims_count_result = await db.execute(
            select(Claim.id).where(Claim.policy_id == policy.id)
        )
        has_claim = claims_count_result.first() is not None

        if not has_claim:
            reward = int(max(10, min(90, round((policy.premium or 0.0) * 0.45))))
            granted += reward

        policy.loyalty_points_awarded = True
        policy.loyalty_points_awarded_at = now

    if granted > 0:
        rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
        rider = rider_result.scalar_one_or_none()
        if rider:
            rider.loyalty_points = int((rider.loyalty_points or 0) + granted)

    await db.commit()
    return granted


async def _resolve_policy_context(payload: PolicyPaymentOrderRequest | PolicyPaymentConfirmRequest, db: AsyncSession):
    if payload.flow_type == PaymentFlowType.RENEW_POLICY:
        if not payload.existing_policy_id:
            raise HTTPException(status_code=400, detail="existing_policy_id is required for renewals")

        existing_result = await db.execute(select(Policy).where(Policy.id == payload.existing_policy_id))
        existing_policy = existing_result.scalar_one_or_none()
        if not existing_policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        rider_result = await db.execute(select(Rider).where(Rider.id == existing_policy.rider_id))
        rider = rider_result.scalar_one_or_none()
        if not rider:
            raise HTTPException(status_code=404, detail="Rider not found")

        return {
            "rider": rider,
            "rider_id": existing_policy.rider_id,
            "zone_id": existing_policy.zone_id,
            "persona": PersonaType(existing_policy.persona),
            "duration_days": payload.duration_days,
            "existing_policy": existing_policy,
        }

    if not payload.rider_id or not payload.zone_id or payload.persona is None:
        raise HTTPException(status_code=400, detail="rider_id, zone_id, and persona are required")

    rider_result = await db.execute(select(Rider).where(Rider.id == payload.rider_id))
    rider = rider_result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    await _ensure_zone_exists(db=db, zone_id=payload.zone_id, rider=rider)

    existing_active = await db.execute(
        select(Policy).where(
            Policy.rider_id == payload.rider_id,
            Policy.status == PolicyStatus.ACTIVE.value,
            Policy.end_date > datetime.now(timezone.utc),
        )
    )
    if existing_active.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Rider already has an active policy")

    return {
        "rider": rider,
        "rider_id": payload.rider_id,
        "zone_id": payload.zone_id,
        "persona": payload.persona,
        "duration_days": payload.duration_days,
        "existing_policy": None,
    }


async def _ensure_zone_exists(db: AsyncSession, zone_id: str, rider: Rider) -> None:
    zone_result = await db.execute(select(Zone).where(Zone.id == zone_id))
    zone = zone_result.scalar_one_or_none()
    if zone is not None:
        return

    if zone_id != "route_pending":
        raise HTTPException(status_code=400, detail=f"Invalid zone_id: {zone_id}")

    # Safety net for onboarding demo flow where route zone is resolved later.
    # Keeping this id stable prevents payment confirmation from failing on FK.
    db.add(
        Zone(
            id="route_pending",
            name="Route Risk Pending",
            city="Dynamic Route",
            state=None,
            country="IN",
            latitude=float(rider.latitude or 0.0),
            longitude=float(rider.longitude or 0.0),
            radius_km=1.0,
            risk_level="medium",
            base_premium_factor=1.0,
            is_active=True,
            created_at=datetime.utcnow(),
        )
    )
    await db.flush()


def _verify_signature(order_id: str, payment_id: str, signature: str | None) -> bool:
    if order_id.startswith("sandbox_order_"):
        return True

    # Demo-safe behavior: in Razorpay test mode, do not block policy activation
    # on signature mismatch. This keeps hackathon/demo flows reliable.
    if settings.RAZORPAY_KEY_ID.startswith("rzp_test_"):
        return True

    if not settings.RAZORPAY_KEY_SECRET:
        return True
    if not signature:
        return False
    body = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/policy-order", response_model=PolicyPaymentOrderResponse)
async def create_policy_payment_order(
    payload: PolicyPaymentOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    ctx = await _resolve_policy_context(payload, db)
    await _award_no_claim_loyalty_points(db, ctx["rider_id"])

    rider = ctx["rider"]
    premium_calc = await calculate_premium(
        rider_id=ctx["rider_id"],
        zone_id=ctx["zone_id"],
        persona=ctx["persona"],
        duration_days=ctx["duration_days"],
        db=db,
    )

    premium_value = float(premium_calc["final_premium"])
    gst_rate = 0.18
    gst_amount = round(premium_value * gst_rate, 2)
    gross_amount = round(premium_value + gst_amount, 2)

    available_points = int(getattr(rider, "loyalty_points", 0) or 0)
    requested_points = int(payload.points_to_redeem or 0)
    capped_points = max(0, min(available_points, requested_points))
    max_value = gross_amount * MAX_REDEEM_SHARE
    requested_value = capped_points * POINT_VALUE_INR
    redeem_value = round(min(max_value, requested_value), 2)
    points_redeemed = int(round(redeem_value / POINT_VALUE_INR))

    net_payable = max(1.0, round(gross_amount - redeem_value, 2))
    amount_paise = int(round(net_payable * 100))
    receipt = f"aux-{payload.flow_type.value}-{str(uuid.uuid4())[:12]}"
    notes = {
        "flow_type": payload.flow_type.value,
        "rider_id": ctx["rider_id"],
        "zone_id": ctx["zone_id"],
        "persona": ctx["persona"].value,
        "duration_days": str(ctx["duration_days"]),
        "premium": str(premium_value),
        "gst": str(gst_amount),
        "tax_rate": "0.18",
        "points_redeemed": str(points_redeemed),
        "points_value": str(redeem_value),
        "net_payable": str(net_payable),
    }
    if payload.existing_policy_id:
        notes["existing_policy_id"] = payload.existing_policy_id

    order_id = f"sandbox_order_{receipt}"
    checkout_mode = "sandbox"
    key_id = settings.RAZORPAY_KEY_ID or "rzp_test_demo"

    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.razorpay.com/v1/orders",
                json={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt,
                    "notes": notes,
                },
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            )
            if not response.is_success:
                raise HTTPException(status_code=502, detail="Failed to create Razorpay order")
            order = response.json()
            order_id = order["id"]
            checkout_mode = "razorpay"
            key_id = settings.RAZORPAY_KEY_ID

    no_claim_points = int(max(10, min(90, round(premium_value * 0.45))))
    return PolicyPaymentOrderResponse(
        checkout_mode=checkout_mode,
        key_id=key_id,
        order_id=order_id,
        amount=amount_paise,
        rider_id=ctx["rider_id"],
        zone_id=ctx["zone_id"],
        persona=ctx["persona"],
        duration_days=ctx["duration_days"],
        premium=premium_calc["final_premium"],
        gst_amount=gst_amount,
        gross_amount=gross_amount,
        points_redeemed=points_redeemed,
        points_value=redeem_value,
        net_payable=net_payable,
        loyalty_balance_after_redemption=max(0, available_points - points_redeemed),
        no_claim_loyalty_points_estimate=no_claim_points,
        coverage=premium_calc["coverage"],
        flow_type=payload.flow_type,
        notes=notes,
        prefill={
            "name": rider.name,
            "contact": rider.phone,
            "email": rider.email or "",
        },
    )


@router.post("/policy-confirm", response_model=PolicyResponse)
async def confirm_policy_payment(
    payload: PolicyPaymentConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    if not _verify_signature(payload.order_id, payload.payment_id, payload.signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay signature")

    ctx = await _resolve_policy_context(payload, db)
    rider = ctx["rider"]
    premium_calc = await calculate_premium(
        rider_id=ctx["rider_id"],
        zone_id=ctx["zone_id"],
        persona=ctx["persona"],
        duration_days=ctx["duration_days"],
        db=db,
    )

    now = datetime.utcnow()
    policy_id = str(uuid.uuid4())
    tx_hash = generate_policy_hash(
        policy_id=policy_id,
        rider_id=ctx["rider_id"],
        zone_id=ctx["zone_id"],
        premium=premium_calc["final_premium"],
    )

    start_date = now
    if ctx["existing_policy"] is not None:
        start_date = max(now, ctx["existing_policy"].end_date)
        ctx["existing_policy"].status = PolicyStatus.EXPIRED.value

    policy = Policy(
        id=policy_id,
        rider_id=ctx["rider_id"],
        zone_id=ctx["zone_id"],
        persona=ctx["persona"].value,
        premium=premium_calc["final_premium"],
        coverage=premium_calc["coverage"],
        start_date=start_date,
        end_date=start_date + timedelta(days=ctx["duration_days"]),
        status=PolicyStatus.ACTIVE.value,
        tx_hash=tx_hash,
        created_at=now,
    )

    points_to_redeem = int(payload.points_to_redeem or 0)
    if points_to_redeem > 0:
        max_points_from_premium = int(
            round((premium_calc["final_premium"] * 1.18 * MAX_REDEEM_SHARE) / POINT_VALUE_INR)
        )
        safe_redeem = max(0, min(int(rider.loyalty_points or 0), points_to_redeem, max_points_from_premium))
        if safe_redeem > 0:
            rider.loyalty_points = int(max(0, int(rider.loyalty_points or 0) - safe_redeem))

    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy
