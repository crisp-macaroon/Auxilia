from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
ADMIN_TOKEN_COOKIE = "auxilia_admin_token"
RIDER_TOKEN_COOKIE = "auxilia_rider_token"


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    cookie_name: str,
) -> str | None:
    if credentials is not None and credentials.credentials:
        return credentials.credentials

    cookie_token = request.cookies.get(cookie_name)
    if cookie_token and cookie_token.strip():
        return cookie_token

    return None


def create_access_token(subject: str, role: str = "admin", expires_minutes: int | None = None) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


async def require_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict[str, Any]:
    token = _extract_token(request, credentials, ADMIN_TOKEN_COOKIE)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")

    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    return payload


async def get_optional_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict[str, Any] | None:
    token = _extract_token(request, credentials, ADMIN_TOKEN_COOKIE)
    if token is None:
        return None

    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    return payload


async def require_rider(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict[str, Any]:
    token = _extract_token(request, credentials, RIDER_TOKEN_COOKIE)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing rider token")

    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    if payload.get("role") != "rider":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rider access required")

    return payload
