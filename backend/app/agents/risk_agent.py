"""
RiskAgent - Dynamic risk scoring for riders and zones
Uses real ML models + live data for premium calculation
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple

from app.core.config import settings
from app.services.weather_service import weather_service
from app.services.traffic_service import traffic_service
from app.services.news_service import news_service
from app.models.schemas import RiskAssessment, PersonaType

logger = logging.getLogger(__name__)

# Pre-computed zone risk baselines (historical data simulation)
ZONE_BASE_RISK = {
    "BLR-KOR": 0.45,  # Koramangala - moderate traffic
    "BLR-IND": 0.52,  # Indiranagar - high traffic
    "BLR-WHT": 0.38,  # Whitefield - IT corridor, moderate
    "BLR-HSR": 0.42,  # HSR Layout - residential, lower risk
    "MUM-AND": 0.68,  # Andheri - very high traffic/rain risk
    "MUM-BAN": 0.62,  # Bandra - high activity zone
    "MUM-POW": 0.55,  # Powai - moderate
    "DEL-CON": 0.58,  # Connaught Place - high traffic
    "DEL-GUR": 0.48,  # Gurgaon - corporate area
    "HYD-HIB": 0.40,  # HITEC City - planned roads
    "PUN-KOT": 0.35,  # Koregaon Park - relatively safe
    "CHN-ANN": 0.50,  # Anna Nagar - moderate risk
    # Mumbai seed zones
    "andheri-east": 0.66,
    "andheri-west": 0.62,
    "bandra-east": 0.58,
    "bandra-west": 0.55,
    "kurla": 0.70,
    "dadar": 0.67,
    "lower-parel": 0.60,
    "powai": 0.52,
    "malad-west": 0.54,
    "goregaon-east": 0.56,
    "borivali-west": 0.46,
    "thane-west": 0.50,
    "vashi": 0.43,
    "churchgate": 0.64,
    "colaba": 0.52,
}

# Persona risk adjustments
PERSONA_RISK_FACTOR = {
    PersonaType.QCOMMERCE: 1.15,    # Q-commerce: time pressure, more risk
    PersonaType.FOOD_DELIVERY: 1.0  # Food delivery: baseline
}

AGE_BAND_RISK_FACTOR = {
    "18-21": 1.08,
    "22-25": 1.03,
    "26-35": 1.0,
    "36-45": 0.97,
    "46+": 1.02,
}

VEHICLE_RISK_FACTOR = {
    "bike": 1.08,
    "scooter": 1.0,
    "ev_scooter": 1.04,
    "bicycle": 0.94,
}

SHIFT_RISK_FACTOR = {
    "breakfast": 0.96,
    "lunch": 1.0,
    "evening": 1.05,
    "late_night": 1.12,
    "mixed": 1.03,
}

# Seasonal risk factors (monsoon months = higher risk)
MONTHLY_RISK_FACTOR = {
    1: 0.9,   # January - dry
    2: 0.85,  # February - dry
    3: 0.9,   # March - transitional
    4: 0.95,  # April - pre-monsoon
    5: 1.0,   # May - pre-monsoon heat
    6: 1.25,  # June - monsoon starts
    7: 1.35,  # July - peak monsoon
    8: 1.30,  # August - monsoon
    9: 1.20,  # September - monsoon ends
    10: 1.0,  # October - post-monsoon
    11: 0.9,  # November - dry
    12: 0.85  # December - winter, dry
}


class RiskAgent:
    """
    AI agent for dynamic risk assessment.
    
    Combines:
    - Base zone risk (historical data)
    - Real-time weather risk
    - Real-time traffic risk
    - News/incident risk
    - Seasonal factors
    - Persona factors
    - Individual rider history
    """
    
    def __init__(self):
        self._risk_cache: Dict[str, RiskAssessment] = {}

    @staticmethod
    def _fallback_ml_risk(
        base_risk: float,
        weather_risk: float,
        traffic_risk: float,
        incident_risk: float,
        historical_risk: float,
        demographic_risk: float,
    ) -> float:
        return min(
            0.99,
            max(
                0.01,
                (
                    base_risk * 0.35
                    + weather_risk * 0.2
                    + traffic_risk * 0.15
                    + incident_risk * 0.1
                    + historical_risk * 0.1
                    + demographic_risk * 0.1
                ),
            ),
        )
    
    async def assess_rider_risk(
        self,
        rider_id: str,
        zone_id: str,
        persona: PersonaType,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        claim_history: Optional[List[Dict]] = None,
        rider_profile: Optional[Dict] = None,
    ) -> RiskAssessment:
        """
        Calculate comprehensive risk score for a rider.
        Returns risk score (0.0 - 1.0) with breakdown.
        """
        now = datetime.utcnow()
        
        # Get base zone risk
        base_risk = ZONE_BASE_RISK.get(zone_id, 0.5)
        
        async def _zero() -> float:
            return 0.0

        # Get real-time risk factors in parallel
        weather_risk_raw, traffic_risk_raw, incident_risk_raw = await asyncio.gather(
            self._get_weather_risk(lat, lon) if lat and lon else _zero(),
            self._get_traffic_risk(lat, lon) if lat and lon else _zero(),
            self._get_incident_risk(zone_id),
        )
        weather_risk = float(weather_risk_raw)
        traffic_risk = float(traffic_risk_raw)
        incident_risk = float(incident_risk_raw)
        
        # Calculate historical risk from claims
        historical_risk = self._calculate_historical_risk(claim_history or [])
        demographic_risk, segment_summary = self._calculate_demographic_risk(
            rider_profile or {}
        )
        
        month = now.month

        age_band = (rider_profile or {}).get("age_band")
        vehicle_type = (rider_profile or {}).get("vehicle_type")
        shift_type = (rider_profile or {}).get("shift_type")
        tenure_months = (rider_profile or {}).get("tenure_months")

        risk_model_version = "fallback-v1"
        try:
            from app.services.ml_service import risk_ml_service

            ml_risk = risk_ml_service.predict_risk_score(
                zone_id=zone_id,
                zone_base_risk=base_risk,
                weather_risk=weather_risk,
                traffic_risk=traffic_risk,
                incident_risk=incident_risk,
                historical_risk=historical_risk,
                persona=persona,
                age_band=age_band,
                vehicle_type=vehicle_type,
                shift_type=shift_type,
                tenure_months=tenure_months,
                month=month,
            )
            risk_model_version = risk_ml_service.model_version
        except Exception:
            ml_risk = self._fallback_ml_risk(
                base_risk,
                weather_risk,
                traffic_risk,
                incident_risk,
                historical_risk,
                demographic_risk,
            )

        # Keep a lightweight calibration against seasonal + persona prior
        persona_factor = PERSONA_RISK_FACTOR.get(persona, 1.0)
        seasonal_factor = MONTHLY_RISK_FACTOR.get(month, 1.0)
        prior_adjustment = min(1.15, max(0.88, (persona_factor * seasonal_factor) ** 0.20))
        final_risk = max(0.0, min(1.0, ml_risk * prior_adjustment))
        
        # Generate risk factors and recommendations
        risk_factors = self._identify_risk_factors(
            base_risk, weather_risk, traffic_risk, incident_risk, historical_risk
        )
        if demographic_risk >= 0.55:
            risk_factors.append("Rider segment exposure is elevated")
        recommendations = self._generate_recommendations(risk_factors, final_risk)
        recommendations.extend(self._generate_segment_recommendations(segment_summary))
        recommendations = list(dict.fromkeys(recommendations))
        
        assessment = RiskAssessment(
            rider_id=rider_id,
            zone_id=zone_id,
            base_risk_score=round(base_risk, 3),
            weather_risk=round(weather_risk, 3),
            traffic_risk=round(traffic_risk, 3),
            incident_risk=round(incident_risk, 3),
            demographic_risk=round(demographic_risk, 3),
            historical_risk=round(historical_risk, 3),
            final_risk_score=round(final_risk, 3),
            ml_model_version=risk_model_version,
            risk_factors=risk_factors,
            recommendations=recommendations,
            segment_summary=segment_summary,
            assessed_at=now
        )
        
        # Cache the assessment
        self._risk_cache[f"{rider_id}:{zone_id}"] = assessment
        
        return assessment

    async def assess_delivery_risk(
        self,
        rider_id: str,
        zone_id: str,
        persona: PersonaType,
        delivery_lat: float,
        delivery_lon: float,
        city: str,
        state: str,
        country: str,
        claim_history: Optional[List[Dict]] = None,
        rider_profile: Optional[Dict] = None,
    ) -> RiskAssessment:
        """
        Delivery-specific risk that blends local zone and macro regional conditions.
        Used when rider submits delivery coordinates for insurance validity.
        """
        base_assessment = await self.assess_rider_risk(
            rider_id=rider_id,
            zone_id=zone_id,
            persona=persona,
            lat=delivery_lat,
            lon=delivery_lon,
            claim_history=claim_history or [],
            rider_profile=rider_profile or {},
        )

        macro = await news_service.get_macro_incident_score(
            country=country or "India",
            state=state or "",
            city=city or "",
            hours_back=24,
        )

        macro_risk = float(macro.get("score", 0.0))
        delivery_weighted = min(
            1.0,
            base_assessment.final_risk_score * 0.8 + macro_risk * 0.2,
        )

        factors = list(base_assessment.risk_factors)
        if macro_risk >= 0.4:
            factors.append("Regional disruption pressure")

        recommendations = list(base_assessment.recommendations)
        if macro_risk >= 0.5:
            recommendations.append(
                "Macro disruption signals are elevated. Avoid high-pressure corridors."
            )

        return RiskAssessment(
            rider_id=base_assessment.rider_id,
            zone_id=base_assessment.zone_id,
            base_risk_score=base_assessment.base_risk_score,
            weather_risk=base_assessment.weather_risk,
            traffic_risk=base_assessment.traffic_risk,
            incident_risk=max(base_assessment.incident_risk, round(macro_risk, 3)),
            demographic_risk=base_assessment.demographic_risk,
            historical_risk=base_assessment.historical_risk,
            final_risk_score=round(delivery_weighted, 3),
            risk_factors=factors,
            recommendations=recommendations,
            segment_summary=base_assessment.segment_summary,
            assessed_at=datetime.utcnow(),
        )

    def _calculate_demographic_risk(self, rider_profile: Dict) -> Tuple[float, List[str]]:
        age_band = (rider_profile.get("age_band") or "").lower()
        vehicle_type = (rider_profile.get("vehicle_type") or "").lower()
        shift_type = (rider_profile.get("shift_type") or "").lower()
        tenure_months = int(rider_profile.get("tenure_months") or 0)

        age_factor = AGE_BAND_RISK_FACTOR.get(age_band, 1.0)
        vehicle_factor = VEHICLE_RISK_FACTOR.get(vehicle_type, 1.0)
        shift_factor = SHIFT_RISK_FACTOR.get(shift_type, 1.0)

        if tenure_months <= 3:
            tenure_factor = 1.10
        elif tenure_months <= 12:
            tenure_factor = 1.03
        elif tenure_months >= 36:
            tenure_factor = 0.95
        else:
            tenure_factor = 1.0

        combined = min(1.0, max(0.0, ((age_factor + vehicle_factor + shift_factor + tenure_factor) / 4) - 0.2))

        segments: List[str] = []
        if age_band:
            segments.append(f"Age band: {age_band}")
        if vehicle_type:
            segments.append(f"Vehicle: {vehicle_type}")
        if shift_type:
            segments.append(f"Shift: {shift_type}")
        segments.append(f"Tenure: {tenure_months} months")

        return combined, segments

    def _generate_segment_recommendations(self, segment_summary: List[str]) -> List[str]:
        recommendations: List[str] = []
        summary_text = " ".join(segment_summary).lower()
        if "late_night" in summary_text:
            recommendations.append("Late-night riders should avoid isolated delivery corridors when disruption signals spike.")
        if "ev_scooter" in summary_text:
            recommendations.append("EV riders should watch charging coverage and avoid long detours during surge drops.")
        if "tenure: 0 months" in summary_text or "tenure: 1 months" in summary_text or "tenure: 2 months" in summary_text:
            recommendations.append("New riders should prefer familiar delivery clusters until route confidence improves.")
        return recommendations
    
    async def assess_zone_risk(self, zone_id: str) -> Dict:
        """
        Calculate aggregate risk for a zone.
        Used for zone-level analytics and pricing.
        """
        base_risk = ZONE_BASE_RISK.get(zone_id, 0.5)
        
        # Get zone coordinates (would come from database in production)
        from app.agents.trigger_agent import ZONE_CONFIG
        zone = ZONE_CONFIG.get(zone_id, {})
        lat = zone.get("lat", 0)
        lon = zone.get("lon", 0)
        
        weather_risk_raw, traffic_risk_raw, incident_risk_raw = await asyncio.gather(
            self._get_weather_risk(lat, lon),
            self._get_traffic_risk(lat, lon),
            self._get_incident_risk(zone_id),
        )
        weather_risk = float(weather_risk_raw)
        traffic_risk = float(traffic_risk_raw)
        incident_risk = float(incident_risk_raw)
        
        risk_model_version = "fallback-v1"
        try:
            from app.services.ml_service import risk_ml_service

            combined_risk = risk_ml_service.predict_risk_score(
                zone_id=zone_id,
                zone_base_risk=base_risk,
                weather_risk=weather_risk,
                traffic_risk=traffic_risk,
                incident_risk=incident_risk,
                historical_risk=0.2,
                persona=PersonaType.FOOD_DELIVERY,
                age_band="26-35",
                vehicle_type="scooter",
                shift_type="mixed",
                tenure_months=18,
                month=datetime.utcnow().month,
            )
            risk_model_version = risk_ml_service.model_version
        except Exception:
            combined_risk = self._fallback_ml_risk(
                base_risk,
                weather_risk,
                traffic_risk,
                incident_risk,
                0.2,
                0.35,
            )
        
        return {
            "zone_id": zone_id,
            "zone_name": zone.get("name", "Unknown"),
            "base_risk": round(base_risk, 3),
            "weather_risk": round(weather_risk, 3),
            "traffic_risk": round(traffic_risk, 3),
            "incident_risk": round(incident_risk, 3),
            "combined_risk": round(combined_risk, 3),
            "risk_level": self._risk_to_level(combined_risk),
            "premium_multiplier": self.calculate_premium_multiplier(combined_risk),
            "risk_model_version": risk_model_version,
            "assessed_at": datetime.utcnow().isoformat()
        }
    
    async def _get_weather_risk(self, lat: float, lon: float) -> float:
        """Calculate weather-based risk (0-1)."""
        try:
            weather = await weather_service.get_current_weather(lat, lon)
            if not weather:
                return 0.0
            
            risk = 0.0
            
            # Rain risk
            if weather.rain_1h > 0:
                rain_risk = min(1.0, weather.rain_1h / settings.RAIN_THRESHOLD_MM)
                risk = max(risk, rain_risk * 0.8)
            
            # Visibility risk
            if weather.visibility < 5000:  # Less than 5km
                vis_risk = 1.0 - (weather.visibility / 10000)
                risk = max(risk, vis_risk * 0.6)
            
            # Wind risk
            if weather.wind_speed > 10:  # >10 m/s
                wind_risk = min(1.0, (weather.wind_speed - 10) / 20)
                risk = max(risk, wind_risk * 0.5)
            
            # Extreme temperature risk
            if weather.temperature > 40:
                heat_risk = min(1.0, (weather.temperature - 40) / 10)
                risk = max(risk, heat_risk * 0.4)
            
            return min(1.0, risk)
        except Exception as e:
            logger.error(f"Weather risk error: {e}")
            return 0.0
    
    async def _get_traffic_risk(self, lat: float, lon: float) -> float:
        """Calculate traffic-based risk (0-1)."""
        try:
            traffic = await traffic_service.get_traffic_flow(lat, lon)
            if not traffic:
                return 0.0
            
            # Congestion level is already 0-10, normalize to 0-1
            congestion_risk = traffic.congestion_level / 10.0
            
            # Road closure is maximum risk
            if traffic.road_closure:
                return 1.0
            
            return min(1.0, congestion_risk)
        except Exception as e:
            logger.error(f"Traffic risk error: {e}")
            return 0.0
    
    async def _get_incident_risk(self, zone_id: str) -> float:
        """Calculate incident-based risk (0-1)."""
        try:
            from app.agents.trigger_agent import ZONE_CONFIG
            zone = ZONE_CONFIG.get(zone_id, {})
            city = zone.get("city", "Mumbai")
            
            incidents = await news_service.search_incidents(city, hours_back=24)
            
            if not incidents:
                return 0.0
            
            # Count high-severity incidents
            severe_count = len([i for i in incidents if i.severity >= 0.7])
            moderate_count = len([i for i in incidents if 0.4 <= i.severity < 0.7])
            
            # Risk formula
            risk = (severe_count * 0.3 + moderate_count * 0.1) / 5.0
            
            return min(1.0, risk)
        except Exception as e:
            logger.error(f"Incident risk error: {e}")
            return 0.0
    
    def _calculate_historical_risk(self, claim_history: List[Dict]) -> float:
        """Calculate risk based on past claims."""
        if not claim_history:
            return 0.2  # Default for new riders (slight risk premium)
        
        # Count claims in last 90 days
        recent_claims = len([c for c in claim_history if c.get("days_ago", 0) < 90])
        
        # More claims = higher risk
        if recent_claims == 0:
            return 0.1  # Good history
        elif recent_claims == 1:
            return 0.3
        elif recent_claims == 2:
            return 0.5
        else:
            return 0.7  # High claim frequency
    
    def _identify_risk_factors(
        self,
        base: float,
        weather: float,
        traffic: float,
        incident: float,
        historical: float
    ) -> List[str]:
        """Identify significant risk factors."""
        factors = []
        
        if base > 0.5:
            factors.append("High-risk zone")
        if weather > 0.4:
            factors.append("Adverse weather conditions")
        if traffic > 0.5:
            factors.append("Heavy traffic congestion")
        if incident > 0.3:
            factors.append("Recent incidents in area")
        if historical > 0.4:
            factors.append("Elevated claim history")
        
        return factors if factors else ["Normal risk profile"]
    
    def _generate_recommendations(self, factors: List[str], risk: float) -> List[str]:
        """Generate safety/risk recommendations."""
        recommendations = []
        
        if "Adverse weather conditions" in factors:
            recommendations.append("Consider waiting for weather to improve")
        if "Heavy traffic congestion" in factors:
            recommendations.append("Use alternative routes if possible")
        if "Recent incidents in area" in factors:
            recommendations.append("Exercise extra caution in this zone")
        if risk > 0.6:
            recommendations.append("High-risk period - ensure safety equipment")
        
        return recommendations if recommendations else ["Normal operations - stay safe"]
    
    def _risk_to_level(self, risk: float) -> str:
        """Convert risk score to level string."""
        if risk >= 0.7:
            return "high"
        elif risk >= 0.4:
            return "medium"
        return "low"
    
    def calculate_premium_multiplier(self, risk_score: float) -> float:
        """
        Convert risk score to premium multiplier.
        Range: 0.8 (low risk) to 1.5 (high risk)
        """
        return round(0.8 + risk_score * 0.7, 2)
    
    def get_cached_assessment(self, rider_id: str, zone_id: str) -> Optional[RiskAssessment]:
        """Get cached risk assessment if available."""
        return self._risk_cache.get(f"{rider_id}:{zone_id}")


# Singleton instance
risk_agent = RiskAgent()
