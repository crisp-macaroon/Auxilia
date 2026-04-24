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
    weather_router,
    payments_router,
    auth_router,
    ml_ops_router,
    route_risk
)
from app.agents.trigger_agent import trigger_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def ensure_rider_auth_columns() -> None:
    async with engine.begin() as conn:
        statements = [
            ("password_hash", "ALTER TABLE riders ADD COLUMN password_hash VARCHAR(255)"),
            ("age_band", "ALTER TABLE riders ADD COLUMN age_band VARCHAR(30)"),
            ("vehicle_type", "ALTER TABLE riders ADD COLUMN vehicle_type VARCHAR(30)"),
            ("shift_type", "ALTER TABLE riders ADD COLUMN shift_type VARCHAR(30)"),
            ("tenure_months", "ALTER TABLE riders ADD COLUMN tenure_months INTEGER DEFAULT 0"),
            ("earning_model", "ALTER TABLE riders ADD COLUMN earning_model VARCHAR(30) DEFAULT 'per_delivery'"),
            ("avg_order_value", "ALTER TABLE riders ADD COLUMN avg_order_value FLOAT DEFAULT 120.0"),
            ("avg_hourly_income", "ALTER TABLE riders ADD COLUMN avg_hourly_income FLOAT DEFAULT 180.0"),
            ("avg_daily_orders", "ALTER TABLE riders ADD COLUMN avg_daily_orders INTEGER DEFAULT 12"),
            ("avg_km_rate", "ALTER TABLE riders ADD COLUMN avg_km_rate FLOAT DEFAULT 18.0"),
            ("loyalty_points", "ALTER TABLE riders ADD COLUMN loyalty_points INTEGER DEFAULT 0"),
        ]
        for column_name, statement in statements:
            try:
                await conn.exec_driver_sql(statement)
                logger.info("Added riders.%s column", column_name)
            except Exception:
                pass


async def ensure_delivery_checkin_table() -> None:
    async with engine.begin() as conn:
        try:
            await conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS delivery_checkin_events (
                    id VARCHAR(36) PRIMARY KEY,
                    rider_id VARCHAR(36) NOT NULL,
                    order_id VARCHAR(100),
                    assigned_zone_id VARCHAR(50) NOT NULL,
                    assigned_zone_name VARCHAR(100),
                    delivery_latitude FLOAT NOT NULL,
                    delivery_longitude FLOAT NOT NULL,
                    rider_latitude FLOAT,
                    rider_longitude FLOAT,
                    distance_to_zone_center_meters FLOAT,
                    is_delivery_in_coverage_zone BOOLEAN DEFAULT FALSE,
                    eligibility_reason TEXT,
                    computed_risk_score FLOAT DEFAULT 0.0,
                    weather_risk FLOAT DEFAULT 0.0,
                    traffic_risk FLOAT DEFAULT 0.0,
                    incident_risk FLOAT DEFAULT 0.0,
                    assessed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(rider_id) REFERENCES riders(id)
                )
                """
            )
            await conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS idx_delivery_checkins_rider ON delivery_checkin_events (rider_id)"
            )
            logger.info("Ensured delivery_checkin_events table")
        except Exception:
            pass


async def ensure_policy_loyalty_columns() -> None:
    async with engine.begin() as conn:
        statements = [
            ("loyalty_points_awarded", "ALTER TABLE policies ADD COLUMN loyalty_points_awarded BOOLEAN DEFAULT FALSE"),
            ("loyalty_points_awarded_at", "ALTER TABLE policies ADD COLUMN loyalty_points_awarded_at TIMESTAMP"),
        ]
        for column_name, statement in statements:
            try:
                await conn.exec_driver_sql(statement)
                logger.info("Added policies.%s column", column_name)
            except Exception:
                pass


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
        try:
            await conn.exec_driver_sql("ALTER TABLE zones ADD COLUMN earning_index FLOAT DEFAULT 1.0")
            logger.info("Added zones.earning_index column")
        except Exception:
            pass
    await ensure_rider_auth_columns()
    await ensure_delivery_checkin_table()
    await ensure_policy_loyalty_columns()
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
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
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
app.include_router(payments_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(ml_ops_router, prefix="/api/v1")
app.include_router(route_risk.router, prefix="/api/v1")


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
