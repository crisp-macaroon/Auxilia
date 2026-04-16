"""
FraudAgent - AI-powered fraud detection for insurance claims
Multi-factor validation with ML scoring
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from app.core.config import settings
from app.models.schemas import FraudAssessment, ClaimStatus
from app.services.location_service import location_service
from app.services.ml_service import fraud_ml_service

logger = logging.getLogger(__name__)

# Fraud detection thresholds
FRAUD_SCORE_THRESHOLD = 0.7  # Claims above this need manual review
AUTO_REJECT_THRESHOLD = 0.9  # Claims above this are auto-rejected
MAX_CLAIMS_PER_WEEK = 3      # Maximum claims per rider per week
CLAIM_COOLDOWN_HOURS = 24    # Minimum hours between claims


class FraudAgent:
    """
    AI agent for fraud detection and claim validation.
    
    Validation checks:
    1. GPS/Location verification - Was rider in the affected zone?
    2. Duplicate claim prevention - No repeat claims for same event
    3. Claim frequency analysis - Unusual claim patterns
    4. Trigger verification - Was trigger actually active?
    5. Behavioral analysis - Anomaly detection
    """
    
    def __init__(self):
        self._validation_cache: Dict[str, FraudAssessment] = {}
    
    async def validate_claim(
        self,
        claim_id: str,
        rider_id: str,
        zone_id: str,
        trigger_type: str,
        rider_location: Tuple[float, float] = None,
        trigger_timestamp: datetime = None,
        claim_history: List[Dict] = None,
        db_session = None
    ) -> FraudAssessment:
        """
        Run comprehensive fraud validation on a claim.
        Returns FraudAssessment with score and flags.
        """
        now = datetime.utcnow()
        risk_flags = []
        check_results = {}
        
        # Run all validation checks in parallel
        results = await asyncio.gather(
            self._check_location(rider_id, zone_id, rider_location),
            self._check_duplicate(rider_id, zone_id, trigger_type, claim_history or []),
            self._check_frequency(rider_id, claim_history or []),
            self._check_trigger_active(zone_id, trigger_type, trigger_timestamp),
            self._check_behavioral_anomaly(rider_id, claim_history or []),
            return_exceptions=True
        )
        
        # Process location check
        location_valid, location_details = self._extract_result(results[0], (True, {}))
        check_results["location"] = {"passed": location_valid, "details": location_details}
        if not location_valid:
            risk_flags.append("Location verification failed")
        
        # Process duplicate check
        no_duplicate, duplicate_details = self._extract_result(results[1], (True, {}))
        check_results["duplicate"] = {"passed": no_duplicate, "details": duplicate_details}
        if not no_duplicate:
            risk_flags.append("Potential duplicate claim detected")
        
        # Process frequency check
        frequency_ok, frequency_details = self._extract_result(results[2], (True, {}))
        check_results["frequency"] = {"passed": frequency_ok, "details": frequency_details}
        if not frequency_ok:
            risk_flags.append("Unusual claim frequency")
        
        # Process trigger verification
        trigger_valid, trigger_details = self._extract_result(results[3], (True, {}))
        check_results["trigger"] = {"passed": trigger_valid, "details": trigger_details}
        if not trigger_valid:
            risk_flags.append("Trigger not verified")
        
        # Process behavioral analysis
        behavior_ok, behavior_details = self._extract_result(results[4], (True, {}))
        check_results["behavior"] = {"passed": behavior_ok, "details": behavior_details}
        if not behavior_ok:
            risk_flags.append("Behavioral anomaly detected")
        
        # Calculate fraud score
        fraud_score, ml_confidence, model_version = self._calculate_fraud_score(check_results)
        
        # Determine verification status
        if fraud_score >= AUTO_REJECT_THRESHOLD:
            status = "rejected"
        elif fraud_score >= FRAUD_SCORE_THRESHOLD:
            status = "suspicious"
        elif all(r["passed"] for r in check_results.values()):
            status = "verified"
        else:
            status = "pending"
        
        assessment = FraudAssessment(
            claim_id=claim_id,
            rider_id=rider_id,
            fraud_score=round(fraud_score, 3),
            fraud_probability=round(fraud_score, 3),
            risk_flags=risk_flags,
            verification_status=status,
            ml_confidence=round(ml_confidence, 3),
            manual_review_required=fraud_score >= FRAUD_SCORE_THRESHOLD,
            assessment_details={**check_results, "fraud_model_version": model_version},
            assessed_at=now
        )
        
        # Cache the assessment
        self._validation_cache[claim_id] = assessment
        
        return assessment
    
    def _extract_result(self, result, default):
        """Extract result or return default on exception."""
        if isinstance(result, Exception):
            logger.error(f"Validation check error: {result}")
            return default
        return result
    
    async def _check_location(
        self,
        rider_id: str,
        zone_id: str,
        rider_location: Tuple[float, float] = None
    ) -> Tuple[bool, Dict]:
        """
        Verify rider was in the affected zone during trigger.
        """
        details = {"check": "location_verification"}
        
        if not rider_location:
            # No location data - can't verify but don't reject
            details["status"] = "no_location_data"
            details["note"] = "Location verification skipped - no GPS data"
            return True, details
        
        try:
            # Get zone center coordinates
            from app.agents.trigger_agent import ZONE_CONFIG
            zone = ZONE_CONFIG.get(zone_id, {})
            
            if not zone:
                details["status"] = "unknown_zone"
                return True, details  # Unknown zone - can't verify
            
            zone_center = (zone.get("lat", 0), zone.get("lon", 0))
            zone_radius = 5000  # 5km default radius
            
            # Calculate distance
            is_in_zone = location_service.is_within_zone(
                rider_location[0], rider_location[1],
                zone_center, zone_radius
            )
            
            distance = location_service._calculate_distance(
                rider_location[0], rider_location[1],
                zone_center[0], zone_center[1]
            )
            
            details["distance_meters"] = round(distance, 2)
            details["zone_radius"] = zone_radius
            details["in_zone"] = is_in_zone
            
            return is_in_zone, details
            
        except Exception as e:
            logger.error(f"Location check error: {e}")
            details["error"] = str(e)
            return True, details  # Fail open
    
    async def _check_duplicate(
        self,
        rider_id: str,
        zone_id: str,
        trigger_type: str,
        claim_history: List[Dict]
    ) -> Tuple[bool, Dict]:
        """
        Check for duplicate claims for the same event.
        """
        details = {"check": "duplicate_detection"}
        
        # Check claims in last 24 hours for same zone and trigger
        cutoff = datetime.utcnow() - timedelta(hours=CLAIM_COOLDOWN_HOURS)
        
        recent_same_claims = [
            c for c in claim_history
            if c.get("zone_id") == zone_id
            and c.get("trigger_type") == trigger_type
            and c.get("created_at", datetime.min) > cutoff
            and c.get("status") in ["pending", "approved", "paid"]
        ]
        
        has_duplicate = len(recent_same_claims) > 0
        
        details["recent_same_claims"] = len(recent_same_claims)
        details["cooldown_hours"] = CLAIM_COOLDOWN_HOURS
        details["has_duplicate"] = has_duplicate
        
        return not has_duplicate, details
    
    async def _check_frequency(
        self,
        rider_id: str,
        claim_history: List[Dict]
    ) -> Tuple[bool, Dict]:
        """
        Analyze claim frequency for anomalies.
        """
        details = {"check": "frequency_analysis"}
        
        # Count claims in last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_claims = [
            c for c in claim_history
            if c.get("created_at", datetime.min) > week_ago
        ]
        
        claim_count = len(recent_claims)
        is_normal = claim_count < MAX_CLAIMS_PER_WEEK
        
        details["claims_last_7_days"] = claim_count
        details["max_allowed"] = MAX_CLAIMS_PER_WEEK
        details["is_normal"] = is_normal
        
        # Check for patterns (e.g., always claiming same amount)
        if claim_history:
            amounts = [c.get("amount", 0) for c in claim_history[-10:]]
            if len(set(amounts)) == 1 and len(amounts) > 3:
                details["pattern_detected"] = "identical_amounts"
                is_normal = False
        
        return is_normal, details
    
    async def _check_trigger_active(
        self,
        zone_id: str,
        trigger_type: str,
        trigger_timestamp: datetime = None
    ) -> Tuple[bool, Dict]:
        """
        Verify the trigger was actually active at claim time.
        """
        details = {"check": "trigger_verification"}
        
        try:
            from app.agents.trigger_agent import trigger_agent
            
            # Get current trigger status
            signal = trigger_agent.get_latest_signal(zone_id)
            
            if not signal:
                details["status"] = "no_signal_data"
                details["note"] = "Could not verify trigger - no data"
                return True, details  # Fail open
            
            # Check if trigger was active
            active_triggers = signal.get("triggers", [])
            trigger_found = any(
                t.trigger_type.value == trigger_type
                for t in active_triggers
            )
            
            details["trigger_found"] = trigger_found
            details["active_triggers"] = [t.trigger_type.value for t in active_triggers]
            details["checked_at"] = signal.get("checked_at")
            
            return trigger_found, details
            
        except Exception as e:
            logger.error(f"Trigger verification error: {e}")
            details["error"] = str(e)
            return True, details  # Fail open
    
    async def _check_behavioral_anomaly(
        self,
        rider_id: str,
        claim_history: List[Dict]
    ) -> Tuple[bool, Dict]:
        """
        ML-based behavioral anomaly detection.
        """
        details = {"check": "behavioral_analysis"}
        
        if len(claim_history) < 3:
            details["status"] = "insufficient_history"
            return True, details  # New rider - can't analyze
        
        anomaly_score = 0.0
        
        # Check 1: Claims always at same time of day
        claim_hours = [c.get("created_at", datetime.now()).hour for c in claim_history[-10:]]
        if len(set(claim_hours)) == 1:
            anomaly_score += 0.3
            details["same_hour_pattern"] = True
        
        # Check 2: Claims always same day of week
        claim_days = [c.get("created_at", datetime.now()).weekday() for c in claim_history[-10:]]
        if len(set(claim_days)) == 1:
            anomaly_score += 0.2
            details["same_day_pattern"] = True
        
        # Check 3: Rejection rate
        rejected = len([c for c in claim_history if c.get("status") == "rejected"])
        if len(claim_history) > 5 and rejected / len(claim_history) > 0.5:
            anomaly_score += 0.4
            details["high_rejection_rate"] = True
        
        details["anomaly_score"] = round(anomaly_score, 2)
        is_normal = anomaly_score < 0.5
        
        return is_normal, details
    
    def _calculate_fraud_score(self, check_results: Dict) -> Tuple[float, float, str]:
        """
        Calculate overall fraud score from check results.
        """
        feature_payload = {
            "location_fail": 0.0 if check_results.get("location", {}).get("passed", True) else 1.0,
            "duplicate_fail": 0.0 if check_results.get("duplicate", {}).get("passed", True) else 1.0,
            "frequency_fail": 0.0 if check_results.get("frequency", {}).get("passed", True) else 1.0,
            "trigger_fail": 0.0 if check_results.get("trigger", {}).get("passed", True) else 1.0,
            "behavior_fail": 0.0 if check_results.get("behavior", {}).get("passed", True) else 1.0,
            "distance_km": float(check_results.get("location", {}).get("details", {}).get("distance_meters", 0.0) or 0.0) / 1000.0,
            "recent_same_claims": float(check_results.get("duplicate", {}).get("details", {}).get("recent_same_claims", 0.0) or 0.0),
            "claims_last_7_days": float(check_results.get("frequency", {}).get("details", {}).get("claims_last_7_days", 0.0) or 0.0),
            "anomaly_score": float(check_results.get("behavior", {}).get("details", {}).get("anomaly_score", 0.0) or 0.0),
            "high_rejection_rate": 1.0 if check_results.get("behavior", {}).get("details", {}).get("high_rejection_rate") else 0.0,
            "same_hour_pattern": 1.0 if check_results.get("behavior", {}).get("details", {}).get("same_hour_pattern") else 0.0,
            "same_day_pattern": 1.0 if check_results.get("behavior", {}).get("details", {}).get("same_day_pattern") else 0.0,
            "trigger_found": 1.0 if check_results.get("trigger", {}).get("details", {}).get("trigger_found", True) else 0.0,
        }

        try:
            fraud_prob, confidence = fraud_ml_service.predict_fraud_probability(feature_payload)
            return fraud_prob, confidence, fraud_ml_service.model_version
        except Exception:
            # deterministic fallback if model unavailable
            fallback_score = (
                feature_payload["location_fail"] * 0.25
                + feature_payload["duplicate_fail"] * 0.30
                + feature_payload["frequency_fail"] * 0.20
                + feature_payload["trigger_fail"] * 0.15
                + feature_payload["behavior_fail"] * 0.10
            )
            return min(1.0, fallback_score), 0.5, "fallback-v1"
    
    async def quick_validate(
        self,
        rider_id: str,
        zone_id: str,
        claim_history: List[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Quick validation for pre-screening.
        Returns (passed, reason).
        """
        claim_history = claim_history or []
        
        # Check claim frequency
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_count = len([
            c for c in claim_history
            if c.get("created_at", datetime.min) > week_ago
        ])
        
        if recent_count >= MAX_CLAIMS_PER_WEEK:
            return False, f"Maximum {MAX_CLAIMS_PER_WEEK} claims per week exceeded"
        
        # Check cooldown
        if claim_history:
            last_claim = max(claim_history, key=lambda c: c.get("created_at", datetime.min))
            hours_since = (datetime.utcnow() - last_claim.get("created_at", datetime.min)).total_seconds() / 3600
            if hours_since < CLAIM_COOLDOWN_HOURS:
                return False, f"Must wait {CLAIM_COOLDOWN_HOURS} hours between claims"
        
        return True, "Pre-validation passed"
    
    def get_cached_assessment(self, claim_id: str) -> Optional[FraudAssessment]:
        """Get cached fraud assessment."""
        return self._validation_cache.get(claim_id)


# Singleton instance
fraud_agent = FraudAgent()
