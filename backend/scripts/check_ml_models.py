"""
Quick smoke checks for Auxilia ML models.

Usage:
    python scripts/check_ml_models.py
    python scripts/check_ml_models.py --live
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.schemas import PersonaType
from app.services.ml_service import fraud_ml_service, premium_ml_service, risk_ml_service


def _run_offline() -> None:
    print("Risk model version:", risk_ml_service.model_version)
    print("Premium model version:", premium_ml_service.model_version)
    print("Fraud model version:", fraud_ml_service.model_version)

    rider_risk = risk_ml_service.predict_risk_score(
        zone_id="andheri-east",
        zone_base_risk=0.66,
        weather_risk=0.24,
        traffic_risk=0.58,
        incident_risk=0.31,
        historical_risk=0.20,
        persona=PersonaType.QCOMMERCE,
        age_band="22-25",
        vehicle_type="bike",
        shift_type="late_night",
        tenure_months=8,
        month=4,
    )
    print("Sample rider risk:", round(rider_risk, 3), "model:", risk_ml_service.model_version)

    premium_multiplier = premium_ml_service.predict_weekly_multiplier(
        zone_id="andheri-east",
        zone_factor=1.2,
        zone_base_risk=0.66,
        risk_score=rider_risk,
        weather_risk=0.24,
        traffic_risk=0.58,
        incident_risk=0.31,
        historical_risk=0.20,
        persona=PersonaType.QCOMMERCE,
        month=4,
        hour=19,
    )
    print("Sample premium multiplier:", round(premium_multiplier, 3))

    fraud_probability, fraud_confidence = fraud_ml_service.predict_fraud_probability(
        {
            "location_fail": 0.0,
            "duplicate_fail": 1.0,
            "frequency_fail": 0.0,
            "trigger_fail": 0.0,
            "behavior_fail": 1.0,
            "distance_km": 1.8,
            "recent_same_claims": 1.0,
            "claims_last_7_days": 2.0,
            "anomaly_score": 0.42,
            "high_rejection_rate": 0.0,
            "same_hour_pattern": 1.0,
            "same_day_pattern": 0.0,
            "trigger_found": 1.0,
        }
    )
    print("Sample fraud probability:", round(fraud_probability, 3), "confidence:", round(fraud_confidence, 3))


async def _run_live() -> None:
    from app.agents.risk_agent import risk_agent
    from app.services.news_service import news_service
    from app.services.traffic_service import traffic_service
    from app.services.weather_service import weather_service

    print("Risk model version:", risk_ml_service.model_version)
    print("Premium model version:", premium_ml_service.model_version)
    print("Fraud model version:", fraud_ml_service.model_version)

    rider_risk = await risk_agent.assess_rider_risk(
        rider_id="smoke-rider",
        zone_id="andheri-east",
        persona=PersonaType.QCOMMERCE,
        lat=19.1136,
        lon=72.8697,
        claim_history=[{"days_ago": 12}, {"days_ago": 44}],
        rider_profile={
            "age_band": "22-25",
            "vehicle_type": "bike",
            "shift_type": "late_night",
            "tenure_months": 8,
        },
    )
    print("Sample rider risk:", rider_risk.final_risk_score, "model:", rider_risk.ml_model_version)

    premium_multiplier = premium_ml_service.predict_weekly_multiplier(
        zone_id="andheri-east",
        zone_factor=1.2,
        zone_base_risk=0.66,
        risk_score=rider_risk.final_risk_score,
        weather_risk=rider_risk.weather_risk,
        traffic_risk=rider_risk.traffic_risk,
        incident_risk=rider_risk.incident_risk,
        historical_risk=rider_risk.historical_risk,
        persona=PersonaType.QCOMMERCE,
        month=4,
        hour=19,
    )
    print("Sample premium multiplier:", round(premium_multiplier, 3))

    fraud_probability, fraud_confidence = fraud_ml_service.predict_fraud_probability(
        {
            "location_fail": 0.0,
            "duplicate_fail": 1.0,
            "frequency_fail": 0.0,
            "trigger_fail": 0.0,
            "behavior_fail": 1.0,
            "distance_km": 1.8,
            "recent_same_claims": 1.0,
            "claims_last_7_days": 2.0,
            "anomaly_score": 0.42,
            "high_rejection_rate": 0.0,
            "same_hour_pattern": 1.0,
            "same_day_pattern": 0.0,
            "trigger_found": 1.0,
        }
    )
    print("Sample fraud probability:", round(fraud_probability, 3), "confidence:", round(fraud_confidence, 3))

    await weather_service.close()
    await traffic_service.close()
    await news_service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check ML model inference")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call live external APIs during risk check (requires valid API keys)",
    )
    args = parser.parse_args()

    if args.live:
        asyncio.run(_run_live())
    else:
        _run_offline()
