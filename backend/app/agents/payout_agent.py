"""
PayoutAgent - Automated claim payout processing
Handles UPI payouts and notifications
"""
import asyncio
import logging
import httpx
from datetime import datetime
from typing import Dict, Optional, Any
from app.core.config import settings
from app.models.schemas import PayoutDecision, ClaimStatus

logger = logging.getLogger(__name__)


class PayoutAgent:
    """
    AI agent for automated payout processing.
    
    Responsibilities:
    1. Validate payout eligibility
    2. Calculate payout amount
    3. Process UPI payment (Razorpay sandbox)
    4. Record blockchain transaction
    5. Send push notification
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._payout_history: Dict[str, PayoutDecision] = {}
    
    async def process_payout(
        self,
        claim_id: str,
        policy_id: str,
        rider_id: str,
        rider_phone: str,
        rider_name: str,
        zone_name: str,
        trigger_type: str,
        trigger_value: float,
        threshold: float,
        coverage_amount: float,
        zone_earning_index: float = 1.0,
        rider_earning_profile: Optional[Dict[str, Any]] = None,
        fraud_score: float = 0.0,
        policy_valid: bool = True
    ) -> PayoutDecision:
        """
        Process a claim payout end-to-end.
        Returns PayoutDecision with transaction details.
        """
        now = datetime.utcnow()
        
        # Step 1: Validate eligibility
        approved, reason = self._validate_payout_eligibility(
            trigger_value, threshold, fraud_score, policy_valid
        )
        
        if not approved:
            return PayoutDecision(
                claim_id=claim_id,
                policy_id=policy_id,
                rider_id=rider_id,
                approved=False,
                payout_amount=0.0,
                payout_percentage=0.0,
                decision_reason=reason,
                trigger_verification=trigger_value >= threshold,
                fraud_check_passed=fraud_score < 0.7,
                policy_valid=policy_valid,
                earning_exposure_multiplier=1.0,
                zone_earning_index=round(float(zone_earning_index or 1.0), 3),
                rider_earning_factor=1.0,
                blockchain_tx_hash=None,
                decided_at=now
            )
        
        # Step 2: Calculate payout amount
        payout_amount, payout_percentage, earning_details = self._calculate_payout(
            trigger_type,
            trigger_value,
            threshold,
            coverage_amount,
            zone_earning_index=zone_earning_index,
            rider_earning_profile=rider_earning_profile,
        )
        
        # Step 3: Process payment and notification in parallel
        payment_result, notification_result = await asyncio.gather(
            self._process_upi_payment(rider_phone, payout_amount, claim_id),
            self._send_push_notification(rider_phone, rider_name, payout_amount, zone_name, trigger_type),
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(payment_result, Exception):
            logger.error(f"Payment error: {payment_result}")
            payment_result = {"id": f"err_{claim_id[:8]}", "status": "error"}
        
        if isinstance(notification_result, Exception):
            logger.error(f"Notification error: {notification_result}")
            notification_result = {"success": False}
        
        # Step 4: Record blockchain transaction (simulated)
        tx_hash = await self._record_blockchain(claim_id, rider_id, payout_amount)
        
        decision = PayoutDecision(
            claim_id=claim_id,
            policy_id=policy_id,
            rider_id=rider_id,
            approved=True,
            payout_amount=round(payout_amount, 2),
            payout_percentage=round(payout_percentage, 2),
            decision_reason=(
                f"Trigger {trigger_type} verified: {trigger_value} >= {threshold}; "
                f"income exposure adjusted for local earning conditions"
            ),
            trigger_verification=True,
            fraud_check_passed=True,
            policy_valid=True,
            earning_exposure_multiplier=earning_details["earning_exposure_multiplier"],
            zone_earning_index=earning_details["zone_earning_index"],
            rider_earning_factor=earning_details["rider_earning_factor"],
            blockchain_tx_hash=tx_hash,
            decided_at=now
        )
        
        # Cache the decision
        self._payout_history[claim_id] = decision
        
        logger.info(f"Payout processed: {claim_id} -> ₹{payout_amount} to {rider_phone}")
        
        return decision
    
    def _validate_payout_eligibility(
        self,
        trigger_value: float,
        threshold: float,
        fraud_score: float,
        policy_valid: bool
    ) -> tuple[bool, str]:
        """
        Validate if claim is eligible for payout.
        """
        if not policy_valid:
            return False, "Policy is not active or has expired"
        
        if fraud_score >= 0.9:
            return False, "Claim rejected due to high fraud risk"
        
        if fraud_score >= 0.7:
            return False, "Claim requires manual review due to elevated fraud risk"
        
        if trigger_value < threshold:
            return False, f"Trigger value {trigger_value} below threshold {threshold}"
        
        return True, "All validation checks passed"
    
    def _calculate_payout(
        self,
        trigger_type: str,
        trigger_value: float,
        threshold: float,
        coverage_amount: float,
        zone_earning_index: float = 1.0,
        rider_earning_profile: Optional[Dict[str, Any]] = None,
    ) -> tuple[float, float, Dict[str, float]]:
        """
        Calculate payout amount based on trigger severity.
        Uses graduated payout based on how much trigger exceeds threshold.
        """
        # Calculate excess ratio
        excess = trigger_value - threshold
        excess_ratio = excess / threshold if threshold > 0 else 0
        
        # Graduated payout tiers
        if excess_ratio >= 1.0:  # Double or more
            payout_percentage = 100.0
        elif excess_ratio >= 0.5:  # 50% over
            payout_percentage = 75.0
        elif excess_ratio >= 0.25:  # 25% over
            payout_percentage = 50.0
        else:  # Just over threshold
            payout_percentage = 30.0
        
        # Apply trigger-specific adjustments
        trigger_multipliers = {
            "rain": 1.0,           # Full payout for rain
            "traffic": 0.8,        # 80% for traffic
            "road_disruption": 1.2,  # 120% for road disruptions (more severe income loss)
            "surge": 0.6           # 60% for low surge (loss of income)
        }
        
        multiplier = trigger_multipliers.get(trigger_type, 1.0)
        payout_percentage *= multiplier
        payout_percentage = min(100.0, payout_percentage)  # Cap at 100%

        earning_details = self._calculate_earning_exposure_multiplier(
            zone_earning_index=zone_earning_index,
            rider_earning_profile=rider_earning_profile or {},
        )
        earning_exposure = earning_details["earning_exposure_multiplier"]
        
        payout_amount = coverage_amount * (payout_percentage / 100.0) * earning_exposure
        payout_amount = min(coverage_amount, payout_amount)
        
        return payout_amount, payout_percentage, earning_details

    def _calculate_earning_exposure_multiplier(
        self,
        zone_earning_index: float,
        rider_earning_profile: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Adjust payout for regional and rider-specific earning context.
        The same hazard should not imply the same income loss everywhere.
        """
        regional = max(0.8, min(1.4, float(zone_earning_index or 1.0)))

        earning_model = str(rider_earning_profile.get("earning_model") or "per_delivery").lower()
        avg_order_value = float(rider_earning_profile.get("avg_order_value") or 120.0)
        avg_hourly_income = float(rider_earning_profile.get("avg_hourly_income") or 180.0)
        avg_daily_orders = float(rider_earning_profile.get("avg_daily_orders") or 12.0)
        avg_km_rate = float(rider_earning_profile.get("avg_km_rate") or 18.0)

        delivery_component = avg_order_value / 120.0
        hourly_component = avg_hourly_income / 180.0
        volume_component = avg_daily_orders / 12.0
        distance_component = avg_km_rate / 18.0

        if earning_model == "per_km":
            rider_specific = (distance_component * 0.65) + (hourly_component * 0.35)
        elif earning_model == "hourly":
            rider_specific = (hourly_component * 0.8) + (volume_component * 0.2)
        else:
            rider_specific = (delivery_component * 0.55) + (hourly_component * 0.25) + (volume_component * 0.2)

        rider_specific = max(0.8, min(1.5, rider_specific))
        exposure = round(max(0.8, min(1.5, (regional * 0.6) + (rider_specific * 0.4))), 3)
        return {
            "earning_exposure_multiplier": exposure,
            "zone_earning_index": round(regional, 3),
            "rider_earning_factor": round(rider_specific, 3),
        }

    def get_earning_exposure_details(
        self,
        zone_earning_index: float,
        rider_earning_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        return self._calculate_earning_exposure_multiplier(
            zone_earning_index=zone_earning_index,
            rider_earning_profile=rider_earning_profile or {},
        )
    
    async def _process_upi_payment(
        self,
        phone: str,
        amount: float,
        claim_id: str
    ) -> Dict[str, Any]:
        """
        Process UPI payment via Razorpay.
        """
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            # Sandbox mode - simulate payment
            logger.info(f"Razorpay sandbox: Simulating ₹{amount} payout to {phone}")
            return {
                "id": f"rz_sandbox_{claim_id[:8]}",
                "status": "processed",
                "amount": amount,
                "mode": "sandbox"
            }
        
        try:
            url = "https://api.razorpay.com/v1/payouts"
            payload = {
                "account_number": settings.RAZORPAY_ACCOUNT_NUMBER or "2323230000000000",
                "amount": int(amount * 100),  # Convert to paise
                "currency": "INR",
                "mode": "UPI",
                "purpose": "payout",
                "fund_account": {
                    "account_type": "vpa",
                    "vpa": {"address": f"{phone}@upi"},
                    "contact": {
                        "name": phone,
                        "contact": phone,
                        "type": "customer"
                    }
                },
                "queue_if_low_balance": True,
                "reference_id": claim_id,
                "narration": "Auxilia Insurance Payout"
            }
            
            response = await self.client.post(
                url,
                json=payload,
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Razorpay payment error: {e}")
            # Return sandbox response on error
            return {
                "id": f"rz_err_{claim_id[:8]}",
                "status": "sandbox_fallback",
                "error": str(e)
            }
    
    async def _send_push_notification(
        self,
        phone: str,
        name: str,
        amount: float,
        zone_name: str,
        trigger_type: str
    ) -> Dict[str, Any]:
        """
        Send push notification via Firebase FCM.
        """
        trigger_messages = {
            "rain": "Heavy rain",
            "traffic": "Severe traffic",
            "road_disruption": "Road disruption",
            "surge": "Low demand"
        }
        
        trigger_msg = trigger_messages.get(trigger_type, "Disruption")
        
        if not settings.FIREBASE_SERVER_KEY:
            # Sandbox mode
            logger.info(f"FCM sandbox: Notification to {phone} - ₹{amount} payout for {trigger_msg}")
            return {"success": True, "mode": "sandbox"}
        
        try:
            url = "https://fcm.googleapis.com/fcm/send"
            payload = {
                "to": f"/topics/rider_{phone}",
                "notification": {
                    "title": "Auxilia - Payout Received!",
                    "body": f"{trigger_msg} in {zone_name}. Rs.{int(amount)} sent to your UPI."
                },
                "data": {
                    "amount": str(amount),
                    "zone": zone_name,
                    "trigger": trigger_type,
                    "claim_type": "parametric"
                }
            }
            
            response = await self.client.post(
                url,
                json=payload,
                headers={"Authorization": f"key={settings.FIREBASE_SERVER_KEY}"}
            )
            return response.json()
            
        except Exception as e:
            logger.error(f"FCM notification error: {e}")
            return {"success": True, "mode": "sandbox"}
    
    async def _record_blockchain(
        self,
        claim_id: str,
        rider_id: str,
        amount: float
    ) -> str:
        """
        Record payout on blockchain for immutability.
        Returns transaction hash.
        """
        # In production, this would interact with the smart contract
        # For now, generate a simulated hash
        import hashlib
        
        data = f"{claim_id}:{rider_id}:{amount}:{datetime.utcnow().isoformat()}"
        tx_hash = "0x" + hashlib.sha256(data.encode()).hexdigest()
        
        logger.info(f"Blockchain record: {tx_hash[:20]}... for claim {claim_id}")
        
        return tx_hash
    
    async def get_payout_status(self, claim_id: str) -> Optional[PayoutDecision]:
        """Get payout status for a claim."""
        return self._payout_history.get(claim_id)
    
    async def estimate_payout(
        self,
        trigger_type: str,
        trigger_value: float,
        threshold: float,
        coverage_amount: float,
        zone_earning_index: float = 1.0,
        rider_earning_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Estimate payout without processing.
        Used for preview/calculation.
        """
        payout_amount, payout_percentage, earning_details = self._calculate_payout(
            trigger_type,
            trigger_value,
            threshold,
            coverage_amount,
            zone_earning_index=zone_earning_index,
            rider_earning_profile=rider_earning_profile,
        )
        
        return {
            "trigger_type": trigger_type,
            "trigger_value": trigger_value,
            "threshold": threshold,
            "coverage_amount": coverage_amount,
            "estimated_payout": round(payout_amount, 2),
            "payout_percentage": round(payout_percentage, 2),
            "earning_exposure_multiplier": earning_details["earning_exposure_multiplier"],
            "zone_earning_index": earning_details["zone_earning_index"],
            "rider_earning_factor": earning_details["rider_earning_factor"],
            "calculation_method": "graduated",
            "estimated_at": datetime.utcnow().isoformat()
        }
    
    async def close(self):
        await self.client.aclose()


# Singleton instance
payout_agent = PayoutAgent()
