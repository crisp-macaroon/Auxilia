"""
News API Service
Fetches news for accident/incident detection in zones
Used for parametric insurance triggers based on reported incidents
"""
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.schemas import NewsIncident
import logging
import re

logger = logging.getLogger(__name__)

NEWS_API_BASE_URL = "https://newsapi.org/v2"

# Keywords for incident detection
INCIDENT_KEYWORDS = {
    "accident": ["accident", "crash", "collision", "hit and run", "vehicle accident", "road accident"],
    "weather": ["flood", "flooding", "waterlogging", "heavy rain", "storm", "cyclone", "thunderstorm"],
    "traffic": ["traffic jam", "road blocked", "road closure", "traffic disruption", "gridlock"],
    "infrastructure": ["pothole", "road damage", "bridge collapse", "road cave", "sinkhole"],
    "safety": ["robbery", "theft", "assault", "violence", "unsafe", "danger zone"]
}


class NewsService:
    """
    NewsAPI integration for incident detection.
    Monitors news for accidents and incidents that could trigger insurance payouts.
    """
    
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_incidents(
        self, 
        city: str,
        incident_type: str = None,
        hours_back: int = 24
    ) -> List[NewsIncident]:
        """
        Search news for incidents in a city.
        Returns list of detected incidents with severity scoring.
        """
        try:
            url = f"{NEWS_API_BASE_URL}/everything"
            
            # Build search query
            keywords = []
            if incident_type and incident_type in INCIDENT_KEYWORDS:
                keywords = INCIDENT_KEYWORDS[incident_type]
            else:
                # Search all incident types
                for kw_list in INCIDENT_KEYWORDS.values():
                    keywords.extend(kw_list)
            
            query = f'({" OR ".join(keywords)}) AND {city}'
            
            from_date = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%S")
            
            params = {
                "apiKey": self.api_key,
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "from": from_date,
                "pageSize": 50
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            incidents = []
            for article in data.get("articles", []):
                incident = self._parse_article_to_incident(article, city)
                if incident:
                    incidents.append(incident)
            
            return incidents
        except httpx.HTTPError as e:
            logger.error(f"NewsAPI error: {e}")
            return []
        except Exception as e:
            logger.error(f"News service error: {e}")
            return []
    
    async def get_top_headlines(
        self, 
        city: str = None,
        category: str = "general"
    ) -> List[Dict[str, Any]]:
        """
        Get top headlines for a region.
        """
        try:
            url = f"{NEWS_API_BASE_URL}/top-headlines"
            params = {
                "apiKey": self.api_key,
                "country": "in",
                "category": category,
                "pageSize": 20
            }
            
            if city:
                params["q"] = city
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("articles", [])
        except Exception as e:
            logger.error(f"Headlines error: {e}")
            return []
    
    async def detect_zone_incidents(
        self, 
        zone_name: str,
        city: str
    ) -> Dict[str, Any]:
        """
        Detect incidents in a specific zone.
        Returns aggregated incident data for trigger evaluation.
        """
        try:
            # Search for incidents in the zone/area
            query = f'"{zone_name}" OR "{city}" AND (accident OR crash OR flood OR traffic)'
            
            url = f"{NEWS_API_BASE_URL}/everything"
            params = {
                "apiKey": self.api_key,
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "from": (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S"),
                "pageSize": 20
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Categorize incidents
            categorized = {
                "accidents": 0,
                "weather": 0,
                "traffic": 0,
                "infrastructure": 0,
                "safety": 0,
                "total": 0,
                "articles": []
            }
            
            for article in data.get("articles", []):
                title = article.get("title", "").lower()
                description = article.get("description", "").lower() if article.get("description") else ""
                content = title + " " + description
                
                for category, keywords in INCIDENT_KEYWORDS.items():
                    if any(kw in content for kw in keywords):
                        categorized[category + "s" if category != "safety" else "safety"] += 1
                        categorized["total"] += 1
                        categorized["articles"].append({
                            "title": article.get("title"),
                            "source": article.get("source", {}).get("name"),
                            "url": article.get("url"),
                            "published": article.get("publishedAt"),
                            "category": category
                        })
                        break
            
            return categorized
        except Exception as e:
            logger.error(f"Zone incidents error: {e}")
            return {"accidents": 0, "weather": 0, "traffic": 0, "total": 0, "articles": []}
    
    def _parse_article_to_incident(self, article: Dict, city: str) -> Optional[NewsIncident]:
        """
        Parse a news article to extract incident information.
        """
        title = article.get("title", "").lower()
        description = article.get("description", "").lower() if article.get("description") else ""
        content = title + " " + description
        
        # Detect incident type
        incident_type = None
        for category, keywords in INCIDENT_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                incident_type = category
                break
        
        if not incident_type:
            return None
        
        # Calculate severity (simple heuristic)
        severity = self._calculate_severity(content, incident_type)
        
        # Try to extract location from content
        location = self._extract_location(content, city)
        
        return NewsIncident(
            title=article.get("title", ""),
            description=article.get("description", ""),
            source=article.get("source", {}).get("name", ""),
            url=article.get("url", ""),
            published_at=datetime.fromisoformat(article.get("publishedAt", "").replace("Z", "+00:00")) if article.get("publishedAt") else datetime.utcnow(),
            incident_type=incident_type,
            severity=severity,
            location=location,
            city=city,
            is_trigger_relevant=severity >= 0.5
        )
    
    def _calculate_severity(self, content: str, incident_type: str) -> float:
        """
        Calculate incident severity score (0.0 to 1.0).
        """
        severity = 0.3  # Base severity
        
        # Severity keywords
        high_severity = ["fatal", "death", "killed", "serious", "major", "multiple", "casualties"]
        medium_severity = ["injury", "injured", "damage", "blocked", "disruption"]
        
        if any(word in content for word in high_severity):
            severity = 0.9
        elif any(word in content for word in medium_severity):
            severity = 0.6
        
        # Adjust by incident type
        type_multipliers = {
            "accident": 1.0,
            "weather": 0.9,
            "traffic": 0.5,
            "infrastructure": 0.7,
            "safety": 0.8
        }
        
        severity *= type_multipliers.get(incident_type, 1.0)
        
        return min(1.0, severity)
    
    def _extract_location(self, content: str, city: str) -> str:
        """
        Try to extract specific location from content.
        """
        # Common location patterns in Indian addresses
        patterns = [
            r"near\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:area|road|street|junction|circle|nagar|colony))",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return city
    
    def is_incident_trigger_active(
        self, 
        incidents: List[NewsIncident], 
        threshold: int = None
    ) -> bool:
        """
        Check if incident count exceeds trigger threshold.
        """
        threshold = threshold or settings.INCIDENT_THRESHOLD
        relevant_incidents = [i for i in incidents if i.is_trigger_relevant]
        return len(relevant_incidents) >= threshold
    
    async def close(self):
        await self.client.aclose()


news_service = NewsService()
