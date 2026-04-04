from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, require_admin
from app.models.schemas import AdminLoginRequest, AdminTokenResponse

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
