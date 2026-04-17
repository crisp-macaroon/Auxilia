from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from datetime import datetime


class PersonaType(str, enum.Enum):
    QCOMMERCE = "qcommerce"
    FOOD_DELIVERY = "food_delivery"


class PolicyStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ClaimStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class TriggerType(str, enum.Enum):
    RAIN = "rain"
    TRAFFIC = "traffic"
    SURGE = "surge"
    ROAD_DISRUPTION = "road_disruption"


class RiderStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Rider(Base):
    __tablename__ = "riders"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    persona = Column(Enum(PersonaType), nullable=False)
    zone_id = Column(String(50), nullable=False, index=True)
    age_band = Column(String(30), nullable=True)
    vehicle_type = Column(String(30), nullable=True)
    shift_type = Column(String(30), nullable=True)
    tenure_months = Column(Integer, default=0)
    earning_model = Column(String(30), default="per_delivery")
    avg_order_value = Column(Float, default=120.0)
    avg_hourly_income = Column(Float, default=180.0)
    avg_daily_orders = Column(Integer, default=12)
    avg_km_rate = Column(Float, default=18.0)
    loyalty_points = Column(Integer, default=0)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    risk_score = Column(Float, default=0.5)
    status = Column(Enum(RiderStatus), default=RiderStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    policies = relationship("Policy", back_populates="rider", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="rider", cascade="all, delete-orphan")
    delivery_checkins = relationship(
        "DeliveryCheckInEvent",
        back_populates="rider",
        cascade="all, delete-orphan",
    )


class Zone(Base):
    __tablename__ = "zones"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(10), default="IN")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_km = Column(Float, default=5.0)
    risk_level = Column(String(20), default="medium")  # low, medium, high
    base_premium_factor = Column(Float, default=1.0)
    earning_index = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    policies = relationship("Policy", back_populates="zone")
    trigger_events = relationship("TriggerEvent", back_populates="zone")


class Policy(Base):
    __tablename__ = "policies"
    
    id = Column(String(36), primary_key=True)
    rider_id = Column(String(36), ForeignKey("riders.id"), nullable=False, index=True)
    zone_id = Column(String(50), ForeignKey("zones.id"), nullable=False, index=True)
    persona = Column(Enum(PersonaType), nullable=False)
    premium = Column(Float, nullable=False)
    coverage = Column(Float, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(PolicyStatus), default=PolicyStatus.ACTIVE, index=True)
    tx_hash = Column(String(100), nullable=True)
    loyalty_points_awarded = Column(Boolean, default=False)
    loyalty_points_awarded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    rider = relationship("Rider", back_populates="policies")
    zone = relationship("Zone", back_populates="policies")
    claims = relationship("Claim", back_populates="policy", cascade="all, delete-orphan")


class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(String(36), primary_key=True)
    policy_id = Column(String(36), ForeignKey("policies.id"), nullable=False, index=True)
    rider_id = Column(String(36), ForeignKey("riders.id"), nullable=False, index=True)
    trigger_type = Column(Enum(TriggerType), nullable=False)
    trigger_value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(ClaimStatus), default=ClaimStatus.PENDING, index=True)
    fraud_score = Column(Float, default=0.0)
    ai_decision = Column(Text, nullable=True)
    tx_hash = Column(String(100), nullable=True)
    trigger_event_id = Column(String(36), ForeignKey("trigger_events.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    policy = relationship("Policy", back_populates="claims")
    rider = relationship("Rider", back_populates="claims")
    trigger_event = relationship("TriggerEvent", back_populates="claims")


class TriggerEvent(Base):
    __tablename__ = "trigger_events"
    
    id = Column(String(36), primary_key=True)
    zone_id = Column(String(50), ForeignKey("zones.id"), nullable=False, index=True)
    trigger_type = Column(Enum(TriggerType), nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    source = Column(String(100), nullable=True)  # API source
    raw_data = Column(Text, nullable=True)  # JSON raw response
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    zone = relationship("Zone", back_populates="trigger_events")
    claims = relationship("Claim", back_populates="trigger_event")


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=True)
    tx_type = Column(String(50), nullable=False)  # policy_created, claim_paid, etc.
    tx_hash = Column(String(100), nullable=False, unique=True)
    from_address = Column(String(100), nullable=True)
    to_address = Column(String(100), nullable=True)
    amount = Column(Float, nullable=True)
    gas_used = Column(Float, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)


class DeliveryCheckInEvent(Base):
    __tablename__ = "delivery_checkin_events"

    id = Column(String(36), primary_key=True)
    rider_id = Column(String(36), ForeignKey("riders.id"), nullable=False, index=True)
    order_id = Column(String(100), nullable=True)
    assigned_zone_id = Column(String(50), nullable=False, index=True)
    assigned_zone_name = Column(String(100), nullable=True)
    delivery_latitude = Column(Float, nullable=False)
    delivery_longitude = Column(Float, nullable=False)
    rider_latitude = Column(Float, nullable=True)
    rider_longitude = Column(Float, nullable=True)
    distance_to_zone_center_meters = Column(Float, nullable=True)
    is_delivery_in_coverage_zone = Column(Boolean, default=False)
    eligibility_reason = Column(Text, nullable=True)
    computed_risk_score = Column(Float, default=0.0)
    weather_risk = Column(Float, default=0.0)
    traffic_risk = Column(Float, default=0.0)
    incident_risk = Column(Float, default=0.0)
    assessed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rider = relationship("Rider", back_populates="delivery_checkins")
