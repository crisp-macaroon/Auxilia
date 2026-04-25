"""
News API Service with Gemini AI Analysis.
Fetches delivery-impacting road disruption and incident signals in zones.
Uses Gemini AI to analyze headlines and extract relevant disruption events.
"""
import httpx
import google.generativeai as genai
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.schemas import NewsIncident
from app.services.weather_service import weather_service
from app.services.gemini_model_resolver import resolve_generate_model_name, build_model
import logging
import json

logger = logging.getLogger(__name__)

NEWS_API_BASE_URL = "https://newsapi.org/v2"


class NewsService:
    """
    NewsAPI integration with Gemini AI for intelligent incident detection.
    Uses LLM to accurately identify and classify traffic/road incidents.
    """
    
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
        self._articles_cache: Dict[str, Dict[str, Any]] = {}
        self._cooldown_until: Dict[str, datetime] = {}
        self._gemini_enabled = bool(settings.GEMINI_API_KEY)
        self._model_name = ""
        self._gemini_disabled_until: datetime | None = None
        
        # Initialize Gemini
        if self._gemini_enabled:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._model_name = resolve_generate_model_name(default="gemini-1.5-flash")
                self.model = build_model(self._model_name)
                logger.info("News Gemini model selected: %s", self._model_name)
            except Exception as exc:
                logger.warning("News Gemini init failed, disabling LLM analysis: %s", exc)
                self._gemini_enabled = False
                self.model = None
        else:
            self.model = None
    
    async def search_incidents(
        self, 
        city: str,
        incident_type: str = None,
        hours_back: int = 24
    ) -> List[NewsIncident]:
        """
        Search news for incidents in a city.
        Uses Gemini AI to intelligently filter and classify incidents.
        """
        try:
            # Fetch raw news articles
            articles = await self._fetch_news(city, hours_back)
            
            if not articles:
                return []
            
            # Use Gemini to analyze articles when available
            analyzed_incidents = []
            if self._gemini_enabled and self.model is not None:
                if not self._gemini_disabled_until or datetime.utcnow() >= self._gemini_disabled_until:
                    analyzed_incidents = await self._analyze_with_gemini(articles, city, incident_type)

            if incident_type in (None, "weather", "safety"):
                heatwave_incident = await self._build_heatwave_incident(city)
                if heatwave_incident:
                    analyzed_incidents.append(heatwave_incident)
            
            return analyzed_incidents
        except Exception as e:
            logger.error(f"News service error: {e}")
            return []

    async def _build_heatwave_incident(self, city: str) -> Optional[NewsIncident]:
        """Create a synthetic high-severity incident when live temperature crosses heatwave threshold."""
        weather = await weather_service.get_weather_by_city(city)
        if not weather or not weather.heatwave_flag:
            return None

        location = city if city else settings.DEFAULT_CITY
        temperature = round(float(weather.temperature), 1)
        feels_like = round(float(weather.feels_like), 1)
        threshold = float(settings.HEATWAVE_TEMP_THRESHOLD_C)

        return NewsIncident(
            title=f"Heatwave Alert in {location}",
            description=(
                f"Live weather crossed heat threshold: temp {temperature}C, feels like {feels_like}C "
                f"(threshold {threshold}C). Delivery risk elevated for riders."
            ),
            source="OpenWeatherMap",
            url="",
            published_at=datetime.utcnow(),
            incident_type="weather",
            severity=0.8,
            location=location,
            city=location,
            is_trigger_relevant=True,
        )

    async def get_macro_incident_score(
        self,
        country: str = "India",
        state: str = "",
        city: str = "",
        hours_back: int = 24,
    ) -> Dict[str, Any]:
        """
        Multi-level incident score for national/state/city context.
        Used for dynamic risk assessment beyond just local zone news.
        """
        levels = []

        if country:
            levels.append(("country", country))
        if state:
            levels.append(("state", state))
        if city:
            levels.append(("city", city))

        weighted_score = 0.0
        weights = {"country": 0.2, "state": 0.3, "city": 0.5}
        detail = []

        for level, target in levels:
            incidents = await self.search_incidents(target, hours_back=hours_back)
            if not incidents:
                detail.append({"level": level, "target": target, "count": 0, "score": 0.0})
                continue

            severe = len([i for i in incidents if i.severity >= 0.7])
            moderate = len([i for i in incidents if 0.4 <= i.severity < 0.7])
            score = min(1.0, (severe * 0.25 + moderate * 0.1) / 4.0)
            weighted_score += score * weights.get(level, 0.0)
            detail.append({"level": level, "target": target, "count": len(incidents), "score": round(score, 3)})

        return {
            "score": round(min(1.0, weighted_score), 3),
            "detail": detail,
            "hours_back": hours_back,
        }
    
    async def _fetch_news(self, city: str, hours_back: int = 24) -> List[Dict]:
        """
        Fetch raw news articles from NewsAPI.
        """
        try:
            cache_key = city.strip().lower()
            now = datetime.utcnow()

            # If this city is rate-limited, serve cached data if available.
            cooldown_until = self._cooldown_until.get(cache_key)
            if cooldown_until and now < cooldown_until:
                cached = self._articles_cache.get(cache_key)
                if cached:
                    logger.info(
                        "NewsAPI cooldown active for %s, using cached articles",
                        city,
                    )
                    return cached.get("articles", [])
                logger.info("NewsAPI cooldown active for %s, returning empty", city)
                return []

            url = f"{NEWS_API_BASE_URL}/everything"
            
            # Broad search query - let Gemini do the filtering
            query = f'{city} (traffic OR road closure OR road block OR flood OR weather OR incident OR disruption)'
            
            from_date = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%S")
            
            params = {
                "apiKey": self.api_key,
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "from": from_date,
                "pageSize": 30
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            self._articles_cache[cache_key] = {
                "articles": articles,
                "cached_at": now,
            }
            # Successful response clears cooldown.
            if cache_key in self._cooldown_until:
                del self._cooldown_until[cache_key]

            return articles
        except httpx.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            cache_key = city.strip().lower()

            if status_code == 429:
                # Cool down for 15 minutes and avoid spamming NewsAPI.
                self._cooldown_until[cache_key] = datetime.utcnow() + timedelta(minutes=15)
                cached = self._articles_cache.get(cache_key)
                if cached:
                    logger.warning(
                        "NewsAPI 429 for %s, using cached articles during cooldown",
                        city,
                    )
                    return cached.get("articles", [])
                logger.warning("NewsAPI 429 for %s, no cache available", city)
                return []

            logger.error(f"NewsAPI error: {e}")
            return []
    
    async def _analyze_with_gemini(
        self, 
        articles: List[Dict], 
        city: str,
        incident_type: str = None
    ) -> List[NewsIncident]:
        """
        Use Gemini AI to analyze news articles and extract relevant incidents.
        """
        try:
            # Prepare articles for analysis
            articles_text = []
            for i, article in enumerate(articles[:20]):  # Limit to 20 for API efficiency
                title = article.get("title", "")
                description = article.get("description", "") or ""
                articles_text.append(f"{i+1}. Title: {title}\n   Description: {description}")
            
            articles_combined = "\n\n".join(articles_text)
            
            prompt = f"""Analyze these news headlines from {city}, India and identify ONLY articles that are about ACTUAL traffic or road disruptions that would affect delivery riders and gig workers.

INCLUDE articles about:
- Road disruptions (collisions, crashes, closures, diversions, blocked corridors)
- Traffic disruptions (road blocks, diversions, heavy congestion due to specific events)
- Weather impacts on roads (flooding, waterlogging, storm damage)
- Heatwave and extreme-heat conditions affecting rider safety (especially 42C+)
- Infrastructure issues (unsafe potholes, road cave-ins, bridge issues)
- Safety incidents on roads (robbery on highways, unsafe areas for riders)
- Curfews, local shutdowns, or strike-linked access issues affecting deliveries

EXCLUDE articles about:
- Stock market crashes, economic events, political speeches without delivery impact
- Sports news, entertainment news
- General weather forecasts without road impact
- Crime not related to roads/delivery workers
- Incidents in other countries/cities

For each RELEVANT incident, provide a JSON response in this exact format:
{{
  "incidents": [
    {{
      "article_index": 1,
      "incident_type": "road_disruption|weather|traffic|infrastructure|safety",
      "severity": 0.1 to 1.0,
      "location": "specific area/road name if mentioned, otherwise '{city}'",
      "summary": "brief 1-line summary",
      "is_relevant": true,
      "reasoning": "why this affects delivery riders"
    }}
  ]
}}

If no relevant incidents found, return: {{"incidents": []}}

NEWS ARTICLES:
{articles_combined}

Respond with ONLY valid JSON, no other text."""

            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response (remove markdown code blocks if present)
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            # Parse JSON response
            analysis = json.loads(response_text)
            
            # Convert to NewsIncident objects
            incidents = []
            for item in analysis.get("incidents", []):
                if not item.get("is_relevant", False):
                    continue
                
                idx = item.get("article_index", 1) - 1
                if idx < 0 or idx >= len(articles):
                    continue
                
                article = articles[idx]
                
                # Filter by incident type if specified
                if incident_type and item.get("incident_type") != incident_type:
                    continue
                
                incident = NewsIncident(
                    title=article.get("title", ""),
                    description=item.get("summary", article.get("description", "")),
                    source=article.get("source", {}).get("name", ""),
                    url=article.get("url", ""),
                    published_at=self._parse_date(article.get("publishedAt")),
                    incident_type=item.get("incident_type", "road_disruption"),
                    severity=float(item.get("severity", 0.5)),
                    location=item.get("location", city),
                    city=city,
                    is_trigger_relevant=float(item.get("severity", 0.5)) >= 0.5
                )
                incidents.append(incident)
            
            logger.info(f"Gemini analyzed {len(articles)} articles, found {len(incidents)} relevant incidents")
            return incidents
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return []
        except Exception as e:
            text = str(e).lower()
            if any(marker in text for marker in ["resourceexhausted", "quota", "rate limit", "429"]):
                self._gemini_disabled_until = datetime.utcnow() + timedelta(minutes=5)
            logger.error(f"Gemini analysis error: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse ISO date string to datetime."""
        if not date_str:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return datetime.utcnow()
    
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
        Detect incidents in a specific zone using AI analysis.
        Returns aggregated incident data for trigger evaluation.
        """
        try:
            # Fetch and analyze incidents
            incidents = await self.search_incidents(city, hours_back=24)
            
            # Filter incidents that might be in this zone
            zone_incidents = []
            for incident in incidents:
                if zone_name.lower() in incident.location.lower() or incident.location == city:
                    zone_incidents.append(incident)
            
            # Categorize incidents
            categorized = {
                "road_disruption": 0,
                "weather": 0,
                "traffic": 0,
                "infrastructure": 0,
                "safety": 0,
                "total": len(zone_incidents),
                "articles": [],
                "ai_analyzed": True
            }
            
            for incident in zone_incidents:
                incident_type = incident.incident_type
                if incident_type in categorized:
                    categorized[incident_type] += 1
                elif incident_type == "accident":
                    categorized["road_disruption"] += 1
                
                categorized["articles"].append({
                    "title": incident.title,
                    "source": incident.source,
                    "url": incident.url,
                    "published": incident.published_at.isoformat(),
                    "category": incident.incident_type,
                    "severity": incident.severity,
                    "location": incident.location,
                    "ai_summary": incident.description
                })
            
            return categorized
        except Exception as e:
            logger.error(f"Zone incidents error: {e}")
            return {"road_disruption": 0, "weather": 0, "traffic": 0, "total": 0, "articles": [], "ai_analyzed": False}
    
    async def get_real_time_alerts(self, city: str) -> List[Dict[str, Any]]:
        """
        Get real-time incident alerts for a city.
        Returns high-severity incidents from the last 6 hours.
        """
        try:
            incidents = await self.search_incidents(city, hours_back=6)
            
            alerts = []
            for incident in incidents:
                if incident.severity >= 0.6:
                    alerts.append({
                        "type": incident.incident_type,
                        "title": incident.title,
                        "location": incident.location,
                        "severity": incident.severity,
                        "time": incident.published_at.isoformat(),
                        "source": incident.source,
                        "url": incident.url
                    })
            
            # Sort by severity (highest first)
            alerts.sort(key=lambda x: x["severity"], reverse=True)
            
            return alerts[:10]  # Return top 10 alerts
        except Exception as e:
            logger.error(f"Real-time alerts error: {e}")
            return []
    
    def is_incident_trigger_active(
        self, 
        incidents: List[NewsIncident], 
        threshold: Optional[int] = None
    ) -> bool:
        """
        Check if incident count exceeds trigger threshold.
        """
        threshold = threshold or settings.ROAD_DISRUPTION_THRESHOLD_COUNT
        relevant_incidents = [i for i in incidents if i.is_trigger_relevant]
        return len(relevant_incidents) >= threshold
    
    async def close(self):
        await self.client.aclose()


news_service = NewsService()
