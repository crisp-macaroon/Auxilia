"""
TomTom Traffic API Service
Fetches real-time traffic congestion data for parametric triggers
"""
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.schemas import TrafficData
import logging

logger = logging.getLogger(__name__)

TOMTOM_BASE_URL = "https://api.tomtom.com/traffic/services/4"
TOMTOM_ROUTING_URL = "https://api.tomtom.com/routing/1"
TOMTOM_INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"
OSRM_ROUTING_URL = "https://router.project-osrm.org/route/v1"


class TrafficService:
    """
    TomTom Traffic API integration for real-time congestion data.
    Used for traffic-based parametric insurance triggers.
    """
    
    def __init__(self):
        self.api_key = settings.TOMTOM_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
        self._tomtom_cooldown_until: Optional[datetime] = None
        self._tomtom_warned = False
    
    async def get_traffic_flow(self, lat: float, lon: float, radius: int = 1000) -> Optional[TrafficData]:
        """
        Get traffic flow data for a location.
        Returns congestion level (0-10), average speed, and free flow speed.
        """
        try:
            if self._tomtom_cooldown_until and datetime.utcnow() < self._tomtom_cooldown_until:
                return None

            # TomTom Flow Segment Data API
            url = f"{TOMTOM_BASE_URL}/flowSegmentData/absolute/10/json"
            params = {
                "key": self.api_key,
                "point": f"{lat},{lon}",
                "unit": "KMPH",
                "thickness": 1
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            flow_data = data.get("flowSegmentData", {})
            
            # Calculate congestion level (0-10 scale)
            current_speed = flow_data.get("currentSpeed", 0)
            free_flow_speed = flow_data.get("freeFlowSpeed", 1)
            
            # Congestion = 10 - (current/freeflow * 10)
            # Higher number = more congestion
            if free_flow_speed > 0:
                congestion_level = max(0, min(10, 10 - (current_speed / free_flow_speed * 10)))
            else:
                congestion_level = 0
            
            return TrafficData(
                zone_id="",  # Set by caller
                congestion_level=round(congestion_level, 1),
                average_speed=current_speed,
                free_flow_speed=free_flow_speed,
                current_travel_time=flow_data.get("currentTravelTime", 0),
                free_flow_travel_time=flow_data.get("freeFlowTravelTime", 0),
                confidence=flow_data.get("confidence", 0.0),
                road_closure=flow_data.get("roadClosure", False),
                timestamp=datetime.utcnow()
            )
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response else None
            if status in (401, 403):
                self._tomtom_cooldown_until = datetime.utcnow() + timedelta(minutes=15)
                if not self._tomtom_warned:
                    logger.warning(
                        "TomTom flow API access denied (%s). Pausing traffic flow calls for 15 minutes.",
                        status,
                    )
                    self._tomtom_warned = True
                return None
            logger.error(f"TomTom API error: {e}")
            return None
        except httpx.HTTPError as e:
            logger.error(f"TomTom API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Traffic service error: {e}")
            return None
    
    async def get_traffic_incidents(
        self, 
        bbox: tuple,  # (min_lon, min_lat, max_lon, max_lat)
        categories: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get traffic incidents in a bounding box.
        Categories: Accident, Fog, DangerousConditions, Rain, Ice, Jam, LaneClosed, RoadClosed, etc.
        """
        try:
            if self._tomtom_cooldown_until and datetime.utcnow() < self._tomtom_cooldown_until:
                return []

            # TomTom Traffic Incidents API (v5 endpoint)
            url = TOMTOM_INCIDENTS_URL
            
            min_lon, min_lat, max_lon, max_lat = bbox
            
            params = {
                "key": self.api_key,
                "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
                "fields": "{incidents{type,geometry{type,coordinates},properties{id,iconCategory,magnitudeOfDelay,events{description,code,iconCategory},startTime,endTime,from,to,length,delay,roadNumbers,aci{probabilityOfOccurrence,numberOfReports,lastReportTime}}}}",
                "language": "en-GB",
                "categoryFilter": ",".join(categories) if categories else "0,1,2,3,4,5,6,7,8,9,10,11",
                "timeValidityFilter": "present"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            incidents = []
            for incident in data.get("incidents", []):
                props = incident.get("properties", {})
                geometry = incident.get("geometry", {})
                
                incidents.append({
                    "id": props.get("id"),
                    "category": props.get("iconCategory"),
                    "description": props.get("events", [{}])[0].get("description", ""),
                    "delay_seconds": props.get("delay", 0),
                    "length_meters": props.get("length", 0),
                    "road": props.get("roadNumbers", [""])[0] if props.get("roadNumbers") else "",
                    "from_location": props.get("from", ""),
                    "to_location": props.get("to", ""),
                    "start_time": props.get("startTime"),
                    "end_time": props.get("endTime"),
                    "coordinates": geometry.get("coordinates", []),
                    "severity": self._get_severity(props.get("magnitudeOfDelay", 0))
                })
            
            return incidents
        except httpx.HTTPStatusError as e:
            # Don't break trigger pipeline when incidents endpoint is unavailable.
            status = e.response.status_code if e.response else None
            if status in (401, 403):
                self._tomtom_cooldown_until = datetime.utcnow() + timedelta(minutes=15)
                if not self._tomtom_warned:
                    logger.warning(
                        "TomTom incidents API access denied (%s). Pausing TomTom calls for 15 minutes.",
                        status,
                    )
                    self._tomtom_warned = True
                return []
            logger.warning(
                "Traffic incidents endpoint returned %s, falling back to empty incidents",
                status,
            )
            return []
        except Exception as e:
            logger.error(f"Traffic incidents error: {e}")
            return []
    
    async def get_route_traffic(
        self, 
        origin: tuple,  # (lat, lon)
        destination: tuple,  # (lat, lon)
    ) -> Optional[Dict[str, Any]]:
        """
        Get traffic-aware route information between two points.
        Returns estimated time with/without traffic.
        """
        try:
            if self._tomtom_cooldown_until and datetime.utcnow() < self._tomtom_cooldown_until:
                return await self._get_osrm_route(origin, destination)

            url = f"{TOMTOM_ROUTING_URL}/calculateRoute/{origin[0]},{origin[1]}:{destination[0]},{destination[1]}/json"
            params = {
                "key": self.api_key,
                "traffic": "true",
                "travelMode": "motorcycle",  # Delivery riders typically use bikes/scooters
                "computeTravelTimeFor": "all"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            routes = data.get("routes", [])
            if not routes:
                return None
            
            route = routes[0]
            summary = route.get("summary", {})
            points = (
                route.get("legs", [{}])[0]
                .get("points", [])
            )
            path_coordinates = [
                [float(point.get("latitude")), float(point.get("longitude"))]
                for point in points
                if point.get("latitude") is not None and point.get("longitude") is not None
            ]
            
            return {
                "distance_meters": summary.get("lengthInMeters", 0),
                "travel_time_seconds": summary.get("travelTimeInSeconds", 0),
                "traffic_delay_seconds": summary.get("trafficDelayInSeconds", 0),
                "live_traffic_time": summary.get("liveTrafficIncidentsTravelTimeInSeconds", 0),
                "no_traffic_time": summary.get("noTrafficTravelTimeInSeconds", 0),
                "departure_time": summary.get("departureTime"),
                "arrival_time": summary.get("arrivalTime"),
                "path_coordinates": path_coordinates,
            }
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response else None
            if status in (401, 403):
                self._tomtom_cooldown_until = datetime.utcnow() + timedelta(minutes=15)
                if not self._tomtom_warned:
                    logger.warning(
                        "TomTom route API access denied (%s). Using OSRM fallback for 15 minutes.",
                        status,
                    )
                    self._tomtom_warned = True
                return await self._get_osrm_route(origin, destination)
            logger.warning(
                "TomTom route API unavailable (%s). Falling back to OSRM geometry",
                e,
            )
            return await self._get_osrm_route(origin, destination)
        except Exception as e:
            logger.warning(
                "TomTom route API unavailable (%s). Falling back to OSRM geometry",
                e,
            )
            return await self._get_osrm_route(origin, destination)

    async def _get_osrm_route(
        self,
        origin: tuple,
        destination: tuple,
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback route provider (OSRM) used when TomTom routing is unavailable.
        Returns geometry and approximate timing without live traffic delay.
        """
        try:
            url = (
                f"{OSRM_ROUTING_URL}/driving/"
                f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
            )
            params = {
                "overview": "full",
                "geometries": "geojson",
                "alternatives": "false",
                "steps": "false",
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            routes = data.get("routes", [])
            if not routes:
                return None

            route = routes[0]
            geometry = route.get("geometry", {})
            coordinates = geometry.get("coordinates", [])

            path_coordinates = []
            for coordinate in coordinates:
                if not isinstance(coordinate, list) or len(coordinate) < 2:
                    continue
                lon, lat = coordinate[0], coordinate[1]
                path_coordinates.append([float(lat), float(lon)])

            duration_seconds = int(route.get("duration", 0) or 0)

            return {
                "distance_meters": int(route.get("distance", 0) or 0),
                "travel_time_seconds": duration_seconds,
                "traffic_delay_seconds": 0,
                "live_traffic_time": duration_seconds,
                "no_traffic_time": duration_seconds,
                "departure_time": None,
                "arrival_time": None,
                "path_coordinates": path_coordinates,
                "routing_provider": "osrm_fallback",
            }
        except Exception as e:
            logger.error(f"OSRM fallback routing error: {e}")
            return None
    
    def _get_severity(self, magnitude: int) -> str:
        """Convert TomTom magnitude to severity level"""
        if magnitude >= 4:
            return "severe"
        elif magnitude >= 3:
            return "major"
        elif magnitude >= 2:
            return "moderate"
        elif magnitude >= 1:
            return "minor"
        return "unknown"
    
    def is_congestion_trigger_active(
        self, 
        traffic: TrafficData, 
        threshold: float = None
    ) -> bool:
        """Check if congestion exceeds trigger threshold"""
        threshold = threshold or settings.CONGESTION_THRESHOLD
        return traffic.congestion_level >= threshold
    
    def is_road_closure_active(self, traffic: TrafficData) -> bool:
        """Check if road is closed"""
        return traffic.road_closure
    
    async def close(self):
        await self.client.aclose()


traffic_service = TrafficService()
