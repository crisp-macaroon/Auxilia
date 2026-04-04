"""
Auxilia API Routers
FastAPI route handlers for all endpoints
"""
from app.routers.riders import router as riders_router
from app.routers.policies import router as policies_router
from app.routers.claims import router as claims_router
from app.routers.triggers import router as triggers_router
from app.routers.zones import router as zones_router
from app.routers.dashboard import router as dashboard_router
from app.routers.weather import router as weather_router
from app.routers.payments import router as payments_router
from app.routers.auth import router as auth_router

__all__ = [
    "riders_router",
    "policies_router",
    "claims_router",
    "triggers_router",
    "zones_router",
    "dashboard_router",
    "weather_router",
    "payments_router",
    "auth_router",
]
