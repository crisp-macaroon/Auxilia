"""
TriggerAgent - Real-time parametric trigger monitoring
Polls weather, traffic, news, and surge APIs to detect insurance triggers
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.core.config import settings
from app.services.weather_service import weather_service
from app.services.traffic_service import traffic_service
from app.services.news_service import news_service
from app.services.surge_service import surge_service
from app.models.schemas import TriggerStatus, TriggerType

logger = logging.getLogger(__name__)

# Zone configuration - Indian cities for gig workers
ZONE_CONFIG = {
    "BLR-KOR": {"name": "Koramangala", "city": "Bengaluru", "lat": 12.9352, "lon": 77.6245},
    "BLR-IND": {"name": "Indiranagar", "city": "Bengaluru", "lat": 12.9784, "lon": 77.6408},
    "BLR-WHT": {"name": "Whitefield", "city": "Bengaluru", "lat": 12.9698, "lon": 77.7500},
    "BLR-HSR": {"name": "HSR Layout", "city": "Bengaluru", "lat": 12.9116, "lon": 77.6389},
    "MUM-AND": {"name": "Andheri", "city": "Mumbai", "lat": 19.1136, "lon": 72.8697},
    "MUM-BAN": {"name": "Bandra", "city": "Mumbai", "lat": 19.0596, "lon": 72.8295},
    "MUM-POW": {"name": "Powai", "city": "Mumbai", "lat": 19.1176, "lon": 72.9060},
    "DEL-CON": {"name": "Connaught Place", "city": "Delhi", "lat": 28.6315, "lon": 77.2167},
    "DEL-GUR": {"name": "Gurgaon", "city": "Gurgaon", "lat": 28.4595, "lon": 77.0266},
    "HYD-HIB": {"name": "HITEC City", "city": "Hyderabad", "lat": 17.4435, "lon": 78.3772},
    "PUN-KOT": {"name": "Koregaon Park", "city": "Pune", "lat": 18.5362, "lon": 73.8939},
    "CHN-ANN": {"name": "Anna Nagar", "city": "Chennai", "lat": 13.0850, "lon": 80.2101},
}


class TriggerAgent:
    """
    Autonomous agent that monitors multiple data sources for parametric triggers.
    
    Triggers monitored:
    - Rain: OpenWeatherMap API (>15mm/hour)
    - Traffic: TomTom API (congestion level >7)
    - Incidents: NewsAPI (accidents/disruptions in zone)
    - Surge: Platform surge data (multiplier <0.8 = low demand)
    """
    
    def __init__(self):
        self._signals: Dict[str, Dict] = {}  # zone_id -> latest signals
        self._active_triggers: Dict[str, List[TriggerStatus]] = {}
        self._poll_interval = settings.TRIGGER_POLL_INTERVAL
        self._running = False
    
    async def check_zone(self, zone_id: str) -> Dict[str, Any]:
        """
        Check all triggers for a specific zone.
        Returns aggregated trigger status.
        """
        if zone_id not in ZONE_CONFIG:
            logger.warning(f"Unknown zone: {zone_id}")
            return {"zone_id": zone_id, "error": "Unknown zone"}
        
        zone = ZONE_CONFIG[zone_id]
        lat, lon = zone["lat"], zone["lon"]
        city = zone["city"]
        
        # Run all checks in parallel
        results = await asyncio.gather(
            self._check_rain(zone_id, lat, lon),
            self._check_traffic(zone_id, lat, lon),
            self._check_incidents(zone_id, city),
            self._check_surge(zone_id, lat, lon),
            return_exceptions=True
        )
        
        triggers = []
        
        # Process rain trigger
        if not isinstance(results[0], Exception) and results[0]:
            triggers.append(results[0])
        
        # Process traffic trigger
        if not isinstance(results[1], Exception) and results[1]:
            triggers.append(results[1])
        
        # Process incident trigger
        if not isinstance(results[2], Exception) and results[2]:
            triggers.append(results[2])
        
        # Process surge trigger
        if not isinstance(results[3], Exception) and results[3]:
            triggers.append(results[3])
        
        # Store signals
        self._signals[zone_id] = {
            "zone_name": zone["name"],
            "city": city,
            "triggers": triggers,
            "active_count": len([trigger for trigger in triggers if trigger.is_active]),
            "checked_at": datetime.utcnow().isoformat()
        }

        self._active_triggers[zone_id] = [trigger for trigger in triggers if trigger.is_active]
        
        return self._signals[zone_id]
    
    async def check_all_zones(self) -> Dict[str, Any]:
        """Check triggers for all configured zones."""
        results = {}
        
        for zone_id in ZONE_CONFIG:
            try:
                result = await self.check_zone(zone_id)
                results[zone_id] = result
            except Exception as e:
                logger.error(f"Error checking zone {zone_id}: {e}")
                results[zone_id] = {"error": str(e)}
        
        return results
    
    async def _check_rain(self, zone_id: str, lat: float, lon: float) -> Optional[TriggerStatus]:
        """Check rain trigger using OpenWeatherMap."""
        try:
            weather = await weather_service.get_current_weather(lat, lon)
            if not weather:
                return None
            
            threshold = settings.RAIN_THRESHOLD_MM
            is_active = weather.rain_1h >= threshold or weather.rain_3h >= threshold
            current_value = max(weather.rain_1h, weather.rain_3h / 3)  # Normalize to hourly
            
            return TriggerStatus(
                zone_id=zone_id,
                zone_name=ZONE_CONFIG[zone_id]["name"],
                trigger_type=TriggerType.RAIN,
                current_value=round(current_value, 2),
                threshold=threshold,
                is_active=is_active,
                affected_policies=0,  # Will be filled by caller
                last_updated=datetime.utcnow(),
                source="OpenWeatherMap"
            )
        except Exception as e:
            logger.error(f"Rain check error for {zone_id}: {e}")
            return None
    
    async def _check_traffic(self, zone_id: str, lat: float, lon: float) -> Optional[TriggerStatus]:
        """Check traffic congestion using TomTom."""
        try:
            traffic = await traffic_service.get_traffic_flow(lat, lon)
            if not traffic:
                return None
            
            threshold = settings.CONGESTION_THRESHOLD
            is_active = traffic.congestion_level >= threshold
            
            return TriggerStatus(
                zone_id=zone_id,
                zone_name=ZONE_CONFIG[zone_id]["name"],
                trigger_type=TriggerType.TRAFFIC,
                current_value=round(traffic.congestion_level, 1),
                threshold=threshold,
                is_active=is_active,
                affected_policies=0,
                last_updated=datetime.utcnow(),
                source="TomTom"
            )
        except Exception as e:
            logger.error(f"Traffic check error for {zone_id}: {e}")
            return None
    
    async def _check_incidents(self, zone_id: str, city: str) -> Optional[TriggerStatus]:
        """Check for road disruptions/incidents using NewsAPI."""
        try:
            incidents = await news_service.search_incidents(city, "road disruption", hours_back=6)
            
            threshold = settings.INCIDENT_THRESHOLD
            relevant_count = len([i for i in incidents if i.is_trigger_relevant])
            is_active = relevant_count >= threshold
            
            return TriggerStatus(
                zone_id=zone_id,
                zone_name=ZONE_CONFIG[zone_id]["name"],
                trigger_type=TriggerType.ROAD_DISRUPTION,
                current_value=float(relevant_count),
                threshold=float(threshold),
                is_active=is_active,
                affected_policies=0,
                last_updated=datetime.utcnow(),
                source="NewsAPI"
            )
        except Exception as e:
            logger.error(f"Incident check error for {zone_id}: {e}")
            return None
    
    async def _check_surge(self, zone_id: str, lat: float, lon: float) -> Optional[TriggerStatus]:
        """Check platform surge (low demand = loss of income)."""
        try:
            surge = await surge_service.get_current_surge(zone_id, lat, lon)
            
            # Low surge means low demand = riders earning less
            threshold = settings.SURGE_THRESHOLD
            is_active = surge.surge_multiplier < threshold
            
            return TriggerStatus(
                zone_id=zone_id,
                zone_name=ZONE_CONFIG[zone_id]["name"],
                trigger_type=TriggerType.SURGE,
                current_value=round(surge.surge_multiplier, 2),
                threshold=threshold,
                is_active=is_active,
                affected_policies=0,
                last_updated=datetime.utcnow(),
                source="SurgeService"
            )
        except Exception as e:
            logger.error(f"Surge check error for {zone_id}: {e}")
            return None
    
    def get_active_triggers(self, zone_id: str = None) -> Dict[str, List[TriggerStatus]]:
        """Get currently active triggers."""
        if zone_id:
            return {zone_id: self._active_triggers.get(zone_id, [])}
        return self._active_triggers
    
    def get_latest_signal(self, zone_id: str) -> Optional[Dict]:
        """Get latest signal data for a zone."""
        return self._signals.get(zone_id)
    
    def get_all_signals(self) -> Dict[str, Dict]:
        """Get all latest signals."""
        return self._signals
    
    async def poll_loop(self):
        """Background polling loop for continuous monitoring."""
        self._running = True
        logger.info(f"TriggerAgent starting poll loop (interval: {self._poll_interval}s)")
        
        while self._running:
            try:
                logger.info("TriggerAgent polling all zones...")
                await self.check_all_zones()
                
                # Log active triggers
                active_count = sum(len(t) for t in self._active_triggers.values())
                logger.info(f"TriggerAgent: {active_count} active triggers across {len(self._active_triggers)} zones")
                
            except Exception as e:
                logger.error(f"TriggerAgent poll error: {e}")
            
            await asyncio.sleep(self._poll_interval)
    
    def stop(self):
        """Stop the polling loop."""
        self._running = False
        logger.info("TriggerAgent stopped")


# Singleton instance
trigger_agent = TriggerAgent()
