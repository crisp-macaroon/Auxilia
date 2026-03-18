"""
RiskAgent - Dynamic risk scoring for riders and zones
Uses ML model + real-time data for premium calculation
"""
import asyncio
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from pathlib import Path
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
}

# Persona risk adjustments
PERSONA_RISK_FACTOR = {
    PersonaType.QCOMMERCE: 1.15,    # Q-commerce: time pressure, more risk
    PersonaType.FOOD_DELIVERY: 1.0  # Food delivery: baseline
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
        self.model = None
        self._risk_cache: Dict[str, RiskAssessment] = {}
        self._load_model()
    
    def _load_model(self):
        """Load ML model if available."""
        model_path = Path(__file__).parent.parent.parent / "ml" / "risk_model.pkl"
        if model_path.exists():
            try:
                import joblib
                self.model = joblib.load(model_path)
                logger.info("Risk ML model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load ML model: {e}")
                self.model = None
    
    async def assess_rider_risk(
        self,
        rider_id: str,
        zone_id: str,
        persona: PersonaType,
        lat: float = None,
        lon: float = None,
        claim_history: List[Dict] = None
    ) -> RiskAssessment:
        """
        Calculate comprehensive risk score for a rider.
        Returns risk score (0.0 - 1.0) with breakdown.
        """
        now = datetime.utcnow()
        
        # Get base zone risk
        base_risk = ZONE_BASE_RISK.get(zone_id, 0.5)
        
        # Get real-time risk factors in parallel
        weather_risk, traffic_risk, incident_risk = await asyncio.gather(
            self._get_weather_risk(lat, lon) if lat and lon else asyncio.coroutine(lambda: 0.0)(),
            self._get_traffic_risk(lat, lon) if lat and lon else asyncio.coroutine(lambda: 0.0)(),
            self._get_incident_risk(zone_id),
            return_exceptions=True
        )
        
        # Handle exceptions
        weather_risk = weather_risk if not isinstance(weather_risk, Exception) else 0.0
        traffic_risk = traffic_risk if not isinstance(traffic_risk, Exception) else 0.0
        incident_risk = incident_risk if not isinstance(incident_risk, Exception) else 0.0
        
        # Calculate historical risk from claims
        historical_risk = self._calculate_historical_risk(claim_history or [])
        
        # Apply persona factor
        persona_factor = PERSONA_RISK_FACTOR.get(persona, 1.0)
        
        # Apply seasonal factor
        month = now.month
        seasonal_factor = MONTHLY_RISK_FACTOR.get(month, 1.0)
        
        # Combine risk factors
        # Weighted combination: base(40%) + weather(20%) + traffic(15%) + incidents(10%) + history(15%)
        combined_risk = (
            base_risk * 0.40 +
            weather_risk * 0.20 +
            traffic_risk * 0.15 +
            incident_risk * 0.10 +
            historical_risk * 0.15
        )
        
        # Apply multipliers
        final_risk = combined_risk * persona_factor * seasonal_factor
        
        # Clamp to 0-1 range
        final_risk = max(0.0, min(1.0, final_risk))
        
        # Generate risk factors and recommendations
        risk_factors = self._identify_risk_factors(
            base_risk, weather_risk, traffic_risk, incident_risk, historical_risk
        )
        recommendations = self._generate_recommendations(risk_factors, final_risk)
        
        assessment = RiskAssessment(
            rider_id=rider_id,
            zone_id=zone_id,
            base_risk_score=round(base_risk, 3),
            weather_risk=round(weather_risk, 3),
            traffic_risk=round(traffic_risk, 3),
            incident_risk=round(incident_risk, 3),
            historical_risk=round(historical_risk, 3),
            final_risk_score=round(final_risk, 3),
            risk_factors=risk_factors,
            recommendations=recommendations,
            assessed_at=now
        )
        
        # Cache the assessment
        self._risk_cache[f"{rider_id}:{zone_id}"] = assessment
        
        return assessment
    
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
        
        weather_risk, traffic_risk, incident_risk = await asyncio.gather(
            self._get_weather_risk(lat, lon),
            self._get_traffic_risk(lat, lon),
            self._get_incident_risk(zone_id),
            return_exceptions=True
        )
        
        weather_risk = weather_risk if not isinstance(weather_risk, Exception) else 0.0
        traffic_risk = traffic_risk if not isinstance(traffic_risk, Exception) else 0.0
        incident_risk = incident_risk if not isinstance(incident_risk, Exception) else 0.0
        
        combined_risk = (
            base_risk * 0.50 +
            weather_risk * 0.25 +
            traffic_risk * 0.15 +
            incident_risk * 0.10
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
