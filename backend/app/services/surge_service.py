"""
Surge Pricing Service
Simulates platform surge detection for parametric insurance
Monitors delivery platform surge multipliers during high demand periods
"""
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.schemas import SurgeData
import logging
import random
import math

logger = logging.getLogger(__name__)


class SurgeService:
    """
    Surge pricing detection service.
    
    In a real implementation, this would integrate with:
    - Swiggy/Zomato APIs (if available)
    - Uber/Ola APIs for ride surge data
    - Internal platform data
    
    For the hackathon, we simulate surge based on:
    - Time of day patterns
    - Weather conditions
    - Zone demand patterns
    - Historical data
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        # Peak hours in 24h format (typical Indian meal times + late night)
        self.peak_hours = {
            "breakfast": (8, 10),
            "lunch": (12, 14),
            "evening_snacks": (16, 18),
            "dinner": (19, 22),
            "late_night": (23, 1)
        }
        # Weekend multiplier
        self.weekend_multiplier = 1.3
        
    async def get_current_surge(
        self, 
        zone_id: str,
        lat: float,
        lon: float,
        platform: str = "generic"
    ) -> SurgeData:
        """
        Get current surge multiplier for a zone.
        Returns surge data with multiplier and factors.
        """
        now = datetime.now()
        
        # Calculate base surge from time of day
        time_surge = self._calculate_time_surge(now)
        
        # Weekend adjustment
        is_weekend = now.weekday() >= 5
        weekend_factor = self.weekend_multiplier if is_weekend else 1.0
        
        # Zone-specific demand (simulated)
        zone_demand = self._simulate_zone_demand(zone_id, now)
        
        # Calculate final surge multiplier
        base_surge = time_surge * weekend_factor * zone_demand
        
        # Add some randomness for realism (±10%)
        noise = random.uniform(0.9, 1.1)
        surge_multiplier = round(base_surge * noise, 2)
        
        # Cap at reasonable limits
        surge_multiplier = max(1.0, min(3.5, surge_multiplier))
        
        return SurgeData(
            zone_id=zone_id,
            surge_multiplier=surge_multiplier,
            demand_level=self._get_demand_level(surge_multiplier),
            active_riders=random.randint(10, 100),
            pending_orders=random.randint(5, 50),
            avg_delivery_time=self._estimate_delivery_time(surge_multiplier),
            peak_period=self._get_current_peak_period(now),
            is_weekend=is_weekend,
            platform=platform,
            estimated_wait_minutes=int(surge_multiplier * 5),
            timestamp=datetime.utcnow()
        )
    
    async def get_surge_forecast(
        self, 
        zone_id: str,
        hours_ahead: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Predict surge for upcoming hours.
        """
        forecasts = []
        now = datetime.now()
        
        for i in range(hours_ahead):
            future_time = now + timedelta(hours=i)
            time_surge = self._calculate_time_surge(future_time)
            
            is_weekend = future_time.weekday() >= 5
            weekend_factor = self.weekend_multiplier if is_weekend else 1.0
            
            predicted_surge = round(time_surge * weekend_factor, 2)
            
            forecasts.append({
                "hour": future_time.strftime("%H:00"),
                "timestamp": future_time.isoformat(),
                "predicted_surge": predicted_surge,
                "demand_level": self._get_demand_level(predicted_surge),
                "confidence": 0.85 - (i * 0.05)  # Decreasing confidence
            })
        
        return forecasts
    
    async def get_zone_comparison(
        self, 
        zone_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Compare surge across multiple zones.
        """
        comparisons = []
        now = datetime.now()
        
        for zone_id in zone_ids:
            surge_data = await self.get_current_surge(zone_id, 0, 0)
            comparisons.append({
                "zone_id": zone_id,
                "surge_multiplier": surge_data.surge_multiplier,
                "demand_level": surge_data.demand_level,
                "active_riders": surge_data.active_riders,
                "recommendation": self._get_zone_recommendation(surge_data)
            })
        
        # Sort by surge (lower is better for riders)
        comparisons.sort(key=lambda x: x["surge_multiplier"])
        
        return comparisons
    
    def _calculate_time_surge(self, dt: datetime) -> float:
        """
        Calculate surge multiplier based on time of day.
        Uses sinusoidal patterns around peak hours.
        """
        hour = dt.hour + dt.minute / 60.0
        
        surge = 1.0  # Base surge
        
        # Check each peak period
        for period, (start, end) in self.peak_hours.items():
            if start <= end:
                if start <= hour <= end:
                    # Inside peak window
                    mid = (start + end) / 2
                    distance = abs(hour - mid) / ((end - start) / 2)
                    peak_surge = 1.5 + (1 - distance) * 1.0  # 1.5 to 2.5
                    surge = max(surge, peak_surge)
            else:
                # Wraps around midnight (e.g., 23 to 1)
                if hour >= start or hour <= end:
                    surge = max(surge, 1.8)  # Late night surge
        
        return surge
    
    def _simulate_zone_demand(self, zone_id: str, dt: datetime) -> float:
        """
        Simulate zone-specific demand multiplier.
        In production, this would use historical data.
        """
        # Use zone_id hash to create consistent "personality" for each zone
        zone_hash = hash(zone_id) % 100
        
        # Some zones are naturally busier
        base_demand = 0.8 + (zone_hash / 100) * 0.4  # 0.8 to 1.2
        
        # Add day-of-week patterns
        day_factors = {
            0: 0.9,   # Monday
            1: 0.85,  # Tuesday
            2: 0.9,   # Wednesday
            3: 0.95,  # Thursday
            4: 1.1,   # Friday
            5: 1.2,   # Saturday
            6: 1.15   # Sunday
        }
        
        day_factor = day_factors.get(dt.weekday(), 1.0)
        
        return base_demand * day_factor
    
    def _get_demand_level(self, surge: float) -> str:
        """Convert surge multiplier to demand level string."""
        if surge >= 2.5:
            return "extreme"
        elif surge >= 2.0:
            return "very_high"
        elif surge >= 1.5:
            return "high"
        elif surge >= 1.2:
            return "moderate"
        return "normal"
    
    def _get_current_peak_period(self, dt: datetime) -> Optional[str]:
        """Get current peak period name if in one."""
        hour = dt.hour
        
        for period, (start, end) in self.peak_hours.items():
            if start <= end:
                if start <= hour <= end:
                    return period
            else:
                if hour >= start or hour <= end:
                    return period
        
        return None
    
    def _estimate_delivery_time(self, surge: float) -> int:
        """Estimate average delivery time in minutes based on surge."""
        base_time = 25  # Base delivery time in minutes
        surge_factor = 1 + (surge - 1) * 0.3  # 30% increase per surge unit
        return int(base_time * surge_factor)
    
    def _get_zone_recommendation(self, surge_data: SurgeData) -> str:
        """Get recommendation for riders based on zone conditions."""
        if surge_data.surge_multiplier >= 2.0:
            return "High demand zone - good earning potential but may face delays"
        elif surge_data.surge_multiplier >= 1.5:
            return "Moderate demand - balanced workload expected"
        else:
            return "Normal demand - quick deliveries likely"
    
    def is_surge_trigger_active(
        self, 
        surge: SurgeData, 
        threshold: float = None
    ) -> bool:
        """
        Check if surge exceeds trigger threshold.
        Used for loss-of-income protection during low demand.
        """
        threshold = threshold or settings.SURGE_THRESHOLD
        # Trigger when surge is BELOW threshold (low demand = low earnings)
        return surge.surge_multiplier < threshold
    
    def is_high_surge_active(
        self, 
        surge: SurgeData, 
        threshold: float = 2.0
    ) -> bool:
        """
        Check if surge is unusually high.
        Could indicate platform issues or events.
        """
        return surge.surge_multiplier >= threshold
    
    async def close(self):
        await self.client.aclose()


surge_service = SurgeService()
