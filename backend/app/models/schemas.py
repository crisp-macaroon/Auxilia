from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# Enums
class PersonaType(str, Enum):
    QCOMMERCE = "qcommerce"
    FOOD_DELIVERY = "food_delivery"


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ClaimStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class TriggerType(str, Enum):
    RAIN = "rain"
    TRAFFIC = "traffic"
    SURGE = "surge"
    ROAD_DISRUPTION = "road_disruption"


class RiderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


# Rider Schemas
class RiderCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")
    email: Optional[str] = None
    persona: PersonaType
    zone_id: str
    age_band: Optional[str] = None
    vehicle_type: Optional[str] = None
    shift_type: Optional[str] = None
    tenure_months: int = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RiderUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    persona: Optional[PersonaType] = None
    zone_id: Optional[str] = None
    age_band: Optional[str] = None
    vehicle_type: Optional[str] = None
    shift_type: Optional[str] = None
    tenure_months: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[RiderStatus] = None


class RiderResponse(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[str]
    persona: PersonaType
    zone_id: str
    age_band: Optional[str]
    vehicle_type: Optional[str]
    shift_type: Optional[str]
    tenure_months: int = 0
    latitude: Optional[float]
    longitude: Optional[float]
    risk_score: float
    status: RiderStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeliveryCheckInRequest(BaseModel):
    order_id: Optional[str] = None
    delivery_latitude: float
    delivery_longitude: float
    rider_latitude: Optional[float] = None
    rider_longitude: Optional[float] = None


class DeliveryCheckInResponse(BaseModel):
    rider_id: str
    order_id: Optional[str] = None
    assigned_zone_id: Optional[str] = None
    assigned_zone_name: Optional[str] = None
    distance_to_zone_center_meters: Optional[float] = None
    is_delivery_in_coverage_zone: bool
    eligibility_reason: str
    computed_risk_score: float
    weather_risk: float
    traffic_risk: float
    incident_risk: float
    assessed_at: datetime


class RouteRiskRequest(BaseModel):
    rider_latitude: float
    rider_longitude: float
    delivery_latitude: float
    delivery_longitude: float


class RouteRiskResponse(BaseModel):
    path_coordinates: List[List[float]]  # List of [lat, lon]
    incidents: List[dict]
    overall_risk_score: float
    risk_factors: List[str]
    epicenter_multiplier: float


class LocationHistoryCreate(BaseModel):
    latitude: float
    longitude: float
    timestamp: Optional[datetime] = None


# Zone Schemas
class ZoneCreate(BaseModel):
    id: str
    name: str
    city: str
    state: Optional[str] = None
    country: str = "IN"
    latitude: float
    longitude: float
    radius_km: float = 5.0
    risk_level: str = "medium"
    base_premium_factor: float = 1.0


class InsurerZoneCreate(BaseModel):
    insurer_id: Optional[str] = None
    name: str
    city: str
    state: Optional[str] = None
    country: str = "IN"
    latitude: float
    longitude: float
    radius_km: float = 3.0
    risk_level: str = "medium"


class ZoneResponse(BaseModel):
    id: str
    name: str
    city: str
    latitude: float
    longitude: float
    radius_km: float
    risk_level: str
    base_premium_factor: float
    is_active: bool
    
    class Config:
        from_attributes = True


class ZoneWithTriggers(ZoneResponse):
    current_triggers: List["TriggerStatus"] = []


# Policy Schemas
class PolicyCreate(BaseModel):
    rider_id: str
    zone_id: str
    persona: PersonaType
    duration_days: int = Field(default=7, ge=1, le=52)  # Weekly model: default 7 days, max ~1 year in weeks


class PolicyResponse(BaseModel):
    id: str
    rider_id: str
    zone_id: str
    persona: PersonaType
    premium: float
    coverage: float
    start_date: datetime
    end_date: datetime
    status: PolicyStatus
    tx_hash: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PolicyWithRider(PolicyResponse):
    rider_name: str
    rider_phone: str
    zone_name: str


# Claim Schemas
class ClaimCreate(BaseModel):
    policy_id: str
    trigger_type: TriggerType


class ClaimResponse(BaseModel):
    id: str
    policy_id: str
    rider_id: str
    trigger_type: TriggerType
    trigger_value: float
    threshold: float
    amount: float
    status: ClaimStatus
    fraud_score: float
    ai_decision: Optional[str]
    tx_hash: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ClaimWithDetails(ClaimResponse):
    rider_name: str
    zone_name: str
    policy_status: PolicyStatus


# Trigger Schemas
class TriggerStatus(BaseModel):
    zone_id: str
    zone_name: str
    trigger_type: TriggerType
    current_value: float
    threshold: float
    is_active: bool
    affected_policies: int
    last_updated: datetime
    source: str


class TriggerEventCreate(BaseModel):
    zone_id: str
    trigger_type: TriggerType
    value: float
    threshold: float
    source: str
    raw_data: Optional[str] = None


class TriggerEventResponse(BaseModel):
    id: str
    zone_id: str
    trigger_type: TriggerType
    value: float
    threshold: float
    is_active: bool
    source: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Weather Schemas (OpenWeatherMap)
class WeatherData(BaseModel):
    zone_id: str
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    wind_speed: float
    rain_1h: float = 0.0
    rain_3h: float = 0.0
    weather_main: str
    weather_description: str
    clouds: int
    visibility: int
    timestamp: datetime


# Traffic Schemas (TomTom)
class TrafficData(BaseModel):
    zone_id: str
    congestion_level: float  # 0-10 scale
    average_speed: float
    free_flow_speed: float
    current_travel_time: int = 0
    free_flow_travel_time: int = 0
    confidence: float = 0.0
    road_closure: bool = False
    timestamp: datetime


# Location Schemas (OpenStreetMap/Nominatim)
class LocationData(BaseModel):
    latitude: float
    longitude: float
    display_name: str
    place_type: str = ""
    place_class: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    postcode: str = ""
    suburb: str = ""
    road: str = ""
    osm_id: Optional[int] = None
    osm_type: Optional[str] = None
    importance: float = 0.0
    timestamp: datetime


# News/Incident Schemas (NewsAPI)
class NewsIncident(BaseModel):
    title: str
    description: Optional[str] = None
    source: str
    url: str
    published_at: datetime
    incident_type: str  # road_disruption, weather, traffic, infrastructure, safety
    severity: float  # 0.0 to 1.0
    location: str
    city: str
    is_trigger_relevant: bool = False


class AccidentNews(BaseModel):
    zone_id: str
    title: str
    description: str
    source: str
    url: str
    published_at: datetime
    severity: str  # minor, major, fatal


class AccidentData(BaseModel):
    zone_id: str
    total_incidents: int
    incidents: List[AccidentNews]
    timestamp: datetime


# Surge Pricing Schemas
class SurgeData(BaseModel):
    zone_id: str
    surge_multiplier: float  # 1.0 = no surge, 2.0 = double rates
    demand_level: str  # normal, moderate, high, very_high, extreme
    active_riders: int = 0
    pending_orders: int = 0
    avg_delivery_time: int = 25  # minutes
    peak_period: Optional[str] = None
    is_weekend: bool = False
    platform: str = "generic"
    estimated_wait_minutes: int = 10
    timestamp: datetime


# Risk Assessment Schemas
class RiskAssessment(BaseModel):
    rider_id: str
    zone_id: str
    base_risk_score: float
    weather_risk: float = 0.0
    traffic_risk: float = 0.0
    incident_risk: float = 0.0
    demographic_risk: float = 0.0
    historical_risk: float = 0.0
    final_risk_score: float
    risk_factors: List[str] = []
    recommendations: List[str] = []
    segment_summary: List[str] = []
    assessed_at: datetime


# Fraud Detection Schemas
class FraudAssessment(BaseModel):
    claim_id: str
    rider_id: str
    fraud_score: float  # 0.0 to 1.0
    fraud_probability: float
    risk_flags: List[str] = []
    verification_status: str  # pending, verified, suspicious, rejected
    ml_confidence: float = 0.0
    manual_review_required: bool = False
    assessment_details: dict = {}
    assessed_at: datetime


# Payout Schemas
class PayoutDecision(BaseModel):
    claim_id: str
    policy_id: str
    rider_id: str
    approved: bool
    payout_amount: float
    payout_percentage: float
    decision_reason: str
    trigger_verification: bool
    fraud_check_passed: bool
    policy_valid: bool
    blockchain_tx_hash: Optional[str] = None
    decided_at: datetime


class PaymentFlowType(str, Enum):
    NEW_POLICY = "new_policy"
    RENEW_POLICY = "renew_policy"


class PolicyPaymentOrderRequest(BaseModel):
    flow_type: PaymentFlowType = PaymentFlowType.NEW_POLICY
    rider_id: Optional[str] = None
    zone_id: Optional[str] = None
    persona: Optional[PersonaType] = None
    duration_days: int = Field(default=7, ge=1, le=52)
    existing_policy_id: Optional[str] = None


class PolicyPaymentOrderResponse(BaseModel):
    checkout_mode: str
    key_id: str
    order_id: str
    amount: int
    currency: str = "INR"
    rider_id: str
    zone_id: str
    persona: PersonaType
    duration_days: int
    premium: float
    coverage: float
    flow_type: PaymentFlowType
    notes: dict = {}
    prefill: dict = {}


class PolicyPaymentConfirmRequest(BaseModel):
    flow_type: PaymentFlowType = PaymentFlowType.NEW_POLICY
    order_id: str
    payment_id: str
    signature: Optional[str] = None
    rider_id: Optional[str] = None
    zone_id: Optional[str] = None
    persona: Optional[PersonaType] = None
    duration_days: int = Field(default=7, ge=1, le=52)
    existing_policy_id: Optional[str] = None


# Agent Schemas
class AgentAction(BaseModel):
    agent_name: str
    action_type: str
    target_id: str
    input_data: dict = {}
    output_data: dict = {}
    success: bool
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    timestamp: datetime


# Dashboard Stats
class DashboardStats(BaseModel):
    total_policies: int
    active_policies: int
    total_claims: int
    pending_claims: int
    total_premium_collected: float
    total_claims_paid: float
    active_riders: int
    avg_risk_score: float
    active_triggers: int
    loss_ratio: float


class ZoneHeatPoint(BaseModel):
    zone_id: str
    zone_name: str
    city: str
    latitude: float
    longitude: float
    radius_km: float
    active_riders: int
    active_policies: int
    open_claims: int
    avg_risk_score: float
    heat_score: float


# Analytics
class ZoneAnalytics(BaseModel):
    zone_id: str
    zone_name: str
    total_policies: int
    total_claims: int
    total_premium: float
    total_payouts: float
    loss_ratio: float
    avg_risk_score: float


class TriggerAnalytics(BaseModel):
    trigger_type: TriggerType
    total_events: int
    total_claims: int
    total_payouts: float
    avg_trigger_value: float


# Premium Calculation
class PremiumCalculation(BaseModel):
    base_premium: float
    zone_factor: float
    persona_factor: float
    risk_factor: float
    final_premium: float
    coverage: float
    breakdown: dict


# API Response wrapper
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class RiderRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[str] = None
    persona: PersonaType
    zone_id: str
    age_band: Optional[str] = None
    vehicle_type: Optional[str] = None
    shift_type: Optional[str] = None
    tenure_months: int = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RiderLoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{9,14}$")
    password: str = Field(..., min_length=6, max_length=128)


class RiderTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    rider: RiderResponse


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


ZoneWithTriggers.model_rebuild()
