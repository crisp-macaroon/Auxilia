"""
Auxilia - AI-Powered Parametric Insurance Platform
FastAPI Backend Entry Point

DEVTrails 2026 Hackathon Project
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import (
    riders_router,
    policies_router,
    claims_router,
    triggers_router,
    zones_router,
    dashboard_router,
    weather_router
)
from app.agents.trigger_agent import trigger_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle:
    - Create database tables on startup
    - Start background trigger polling
    - Cleanup on shutdown
    """
    logger.info("Starting Auxilia Backend...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
    
    # Start trigger agent polling in background
    polling_task = asyncio.create_task(trigger_agent.poll_loop())
    logger.info("Trigger polling started")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Auxilia Backend...")
    trigger_agent.stop()
    polling_task.cancel()
    
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Auxilia API",
    description="""
    ## AI-Powered Parametric Insurance for Gig Workers
    
    Auxilia provides instant, automated insurance coverage for delivery riders
    based on real-time parametric triggers:
    
    - **Rain Triggers**: OpenWeatherMap API integration
    - **Traffic Triggers**: TomTom API for congestion data  
    - **Incident Triggers**: NewsAPI for road disruption detection
    - **Surge Triggers**: Platform demand monitoring
    
    ### Key Features:
    - Real-time trigger monitoring
    - AI-powered fraud detection
    - Automated claim processing
    - Instant UPI payouts
    - Blockchain transaction logging
    
    ### AI Agents:
    - **TriggerAgent**: Monitors weather, traffic, news, surge data
    - **RiskAgent**: Dynamic risk scoring for premium calculation
    - **FraudAgent**: Multi-factor claim validation
    - **PayoutAgent**: Automated disbursement processing
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(riders_router, prefix="/api/v1")
app.include_router(policies_router, prefix="/api/v1")
app.include_router(claims_router, prefix="/api/v1")
app.include_router(triggers_router, prefix="/api/v1")
app.include_router(zones_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(weather_router, prefix="/api/v1")


@app.get("/")
async def root():
    """API root - health check and info."""
    return {
        "name": "Auxilia API",
        "version": "1.0.0",
        "status": "running",
        "description": "AI-Powered Parametric Insurance for Gig Workers",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check trigger agent status
    signals = trigger_agent.get_all_signals()
    trigger_status = "active" if signals else "initializing"
    
    return {
        "status": "healthy",
        "database": "connected",
        "trigger_agent": trigger_status,
        "monitored_zones": len(signals),
        "api_version": "1.0.0"
    }


@app.get("/api/v1/config")
async def get_api_config():
    """Get API configuration (non-sensitive)."""
    return {
        "trigger_thresholds": {
            "rain_mm": settings.RAIN_THRESHOLD_MM,
            "congestion": settings.CONGESTION_THRESHOLD,
            "surge": settings.SURGE_THRESHOLD,
            "incidents": settings.INCIDENT_THRESHOLD
        },
        "poll_interval_seconds": settings.TRIGGER_POLL_INTERVAL,
        "supported_triggers": ["rain", "traffic", "surge", "road_disruption"],
        "supported_personas": ["qcommerce", "food_delivery"]
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
