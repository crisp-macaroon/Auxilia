"""
Payments API Router
Razorpay order creation and payment confirmation for policy purchases.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import hmac
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.database import Policy, Rider
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

    existing_active = await db.execute(
        select(Policy).where(
            Policy.rider_id == payload.rider_id,
            Policy.status == PolicyStatus.ACTIVE.value,
            Policy.end_date > datetime.utcnow(),
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


def _verify_signature(order_id: str, payment_id: str, signature: str | None) -> bool:
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
    premium_calc = await calculate_premium(
        rider_id=ctx["rider_id"],
        zone_id=ctx["zone_id"],
        persona=ctx["persona"],
        duration_days=ctx["duration_days"],
        db=db,
    )

    amount_paise = int(round(premium_calc["final_premium"] * 100))
    receipt = f"aux-{payload.flow_type.value}-{str(uuid.uuid4())[:12]}"
    notes = {
        "flow_type": payload.flow_type.value,
        "rider_id": ctx["rider_id"],
        "zone_id": ctx["zone_id"],
        "persona": ctx["persona"].value,
        "duration_days": str(ctx["duration_days"]),
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

    rider = ctx["rider"]
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

    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy
