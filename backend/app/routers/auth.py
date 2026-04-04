from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, require_admin, require_rider, verify_password
from app.models.database import Rider, RiderStatus
from app.models.schemas import AdminLoginRequest, AdminTokenResponse, PersonaType, RiderLoginRequest, RiderRegisterRequest, RiderTokenResponse
from app.agents.risk_agent import risk_agent

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/admin/login", response_model=AdminTokenResponse)
async def admin_login(payload: AdminLoginRequest):
    if payload.username != settings.ADMIN_USERNAME or payload.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")

    token = create_access_token(subject=payload.username, role="admin")
    return AdminTokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/admin/me")
async def admin_me(payload: dict = Depends(require_admin)):
    return {
        "username": payload.get("sub"),
        "role": payload.get("role"),
        "exp": payload.get("exp"),
    }


@router.post("/rider/register", response_model=RiderTokenResponse)
async def rider_register(payload: RiderRegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Rider).where(Rider.phone == payload.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already registered")

    risk_assessment = await risk_agent.assess_rider_risk(
        rider_id="new",
        zone_id=payload.zone_id,
        persona=payload.persona,
        lat=payload.latitude,
        lon=payload.longitude,
        claim_history=[],
        rider_profile={
            "age_band": payload.age_band,
            "vehicle_type": payload.vehicle_type,
            "shift_type": payload.shift_type,
            "tenure_months": payload.tenure_months,
        },
    )

    rider = Rider(
        id=str(uuid.uuid4()),
        name=payload.name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        email=payload.email,
        persona=payload.persona.value,
        zone_id=payload.zone_id,
        age_band=payload.age_band,
        vehicle_type=payload.vehicle_type,
        shift_type=payload.shift_type,
        tenure_months=payload.tenure_months,
        latitude=payload.latitude,
        longitude=payload.longitude,
        risk_score=risk_assessment.final_risk_score,
        status=RiderStatus.ACTIVE.value,
        created_at=datetime.utcnow(),
    )
    db.add(rider)
    await db.commit()
    await db.refresh(rider)

    token = create_access_token(subject=rider.id, role="rider")
    return RiderTokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        rider=rider,
    )


@router.post("/rider/login", response_model=RiderTokenResponse)
async def rider_login(payload: RiderLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rider).where(Rider.phone == payload.phone))
    rider = result.scalar_one_or_none()
    if rider is None or not rider.password_hash or not verify_password(payload.password, rider.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid rider credentials")

    token = create_access_token(subject=rider.id, role="rider")
    return RiderTokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        rider=rider,
    )


@router.get("/rider/me", response_model=RiderTokenResponse)
async def rider_me(payload: dict = Depends(require_rider), db: AsyncSession = Depends(get_db)):
    rider_id = payload.get("sub")
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if rider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found")

    token = create_access_token(subject=rider.id, role="rider")
    return RiderTokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        rider=rider,
    )
