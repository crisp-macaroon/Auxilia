import json

from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Auxilia API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./auxilia.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: str | List[str] = ["*"]
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "auxilia123"
    
    # External APIs
    OPENWEATHER_API_KEY: str = ""
    TOMTOM_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
    # Blockchain
    BLOCKCHAIN_RPC_URL: str = "https://rpc-mumbai.maticvigil.com"
    CONTRACT_ADDRESS: str = ""
    WALLET_PRIVATE_KEY: str = ""
    
    # Trigger Thresholds
    RAIN_THRESHOLD_MM: float = 50.0
    TRAFFIC_THRESHOLD_PERCENT: float = 60.0
    SURGE_THRESHOLD_MULTIPLIER: float = 2.5
    ROAD_DISRUPTION_THRESHOLD_COUNT: int = 3
    HEATWAVE_TEMP_THRESHOLD_C: float = 42.0
    # Legacy fallback (deprecated)
    ACCIDENT_THRESHOLD_COUNT: Optional[int] = None
    TRIGGER_POLL_INTERVAL: int = 300
    LOCATION_TRACK_INTERVAL_SECONDS: int = 180
    DELIVERY_ZONE_MAX_RADIUS_KM: float = 5.0

    # Backward-compatible aliases used across routers/agents
    CONGESTION_THRESHOLD: float = 60.0
    SURGE_THRESHOLD: float = 2.5
    INCIDENT_THRESHOLD: int = 3
    
    # Payout Amounts (INR)
    RAIN_PAYOUT: int = 150
    TRAFFIC_PAYOUT: int = 100
    SURGE_PAYOUT: int = 200
    ROAD_DISRUPTION_PAYOUT: int = 500
    # Legacy fallback (deprecated)
    ACCIDENT_PAYOUT: Optional[int] = None

    # Optional payout integrations
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_ACCOUNT_NUMBER: str = ""
    FIREBASE_SERVER_KEY: str = ""
    
    # Zone Configuration - Mumbai
    DEFAULT_CITY: str = "Mumbai"
    DEFAULT_COUNTRY: str = "IN"

    def model_post_init(self, __context) -> None:
        if self.ACCIDENT_THRESHOLD_COUNT is not None:
            self.ROAD_DISRUPTION_THRESHOLD_COUNT = self.ACCIDENT_THRESHOLD_COUNT
        if self.ACCIDENT_PAYOUT is not None:
            self.ROAD_DISRUPTION_PAYOUT = self.ACCIDENT_PAYOUT

        self.CONGESTION_THRESHOLD = self.TRAFFIC_THRESHOLD_PERCENT
        self.SURGE_THRESHOLD = self.SURGE_THRESHOLD_MULTIPLIER
        self.INCIDENT_THRESHOLD = self.ROAD_DISRUPTION_THRESHOLD_COUNT

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return ["*"]
            if cleaned.startswith("["):
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in cleaned.split(",") if item.strip()]
        return value
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
