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
    ROAD_DISRUPTION = "road_disruption"  # Renamed from 'accident' - road incidents affecting income


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
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    risk_score = Column(Float, default=0.5)
    status = Column(Enum(RiderStatus), default=RiderStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    policies = relationship("Policy", back_populates="rider", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="rider", cascade="all, delete-orphan")


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
