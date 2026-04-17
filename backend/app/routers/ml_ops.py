"""
ML Ops Router
Admin endpoints for model status and synthetic evaluation.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends

from app.core.security import require_admin
from app.models.schemas import PersonaType
from app.services.ml_service import (
    fraud_ml_service,
    premium_ml_service,
    risk_ml_service,
)


router = APIRouter(prefix="/ml", tags=["ML Ops"], dependencies=[Depends(require_admin)])


def _artifact_presence() -> dict:
    ml_dir = Path(__file__).resolve().parents[2] / "ml"
    files = {
        "risk_model": (ml_dir / "risk_model.pkl").exists(),
        "premium_model": (ml_dir / "premium_model.pkl").exists(),
        "fraud_model": (ml_dir / "fraud_model.pkl").exists(),
        "risk_meta": (ml_dir / "risk_model_meta.json").exists(),
        "premium_meta": (ml_dir / "premium_model_meta.json").exists(),
        "fraud_meta": (ml_dir / "fraud_model_meta.json").exists(),
    }
    return {
        "ml_dir": str(ml_dir),
        "files": files,
        "all_model_binaries_present": all(files[k] for k in ["risk_model", "premium_model", "fraud_model"]),
    }


@router.get("/status")
async def get_ml_status():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "models": {
            "risk": {
                "version": risk_ml_service.model_version,
                "backend": type(getattr(risk_ml_service, "_model", None)).__name__,
                "loaded": getattr(risk_ml_service, "_model", None) is not None,
            },
            "premium": {
                "version": premium_ml_service.model_version,
                "backend": type(getattr(premium_ml_service, "_model", None)).__name__,
                "loaded": getattr(premium_ml_service, "_model", None) is not None,
            },
            "fraud": {
                "version": fraud_ml_service.model_version,
                "backend": type(getattr(fraud_ml_service, "_model", None)).__name__,
                "loaded": getattr(fraud_ml_service, "_model", None) is not None,
            },
        },
        "artifacts": _artifact_presence(),
    }


def _eval_risk(samples: int = 1200) -> dict:
    rng = np.random.default_rng(1221)
    errors: list[float] = []
    for _ in range(samples):
        zone_base = float(rng.uniform(0.2, 0.85))
        weather = float(rng.beta(1.8, 4.2))
        traffic = float(rng.beta(2.2, 2.7))
        incident = float(rng.beta(1.6, 3.8))
        historical = float(rng.beta(2.0, 5.0))
        age = str(rng.choice(["18-21", "22-25", "26-35", "36-45", "46+"]))
        vehicle = str(rng.choice(["bike", "scooter", "ev_scooter", "bicycle"]))
        shift = str(rng.choice(["breakfast", "lunch", "evening", "late_night", "mixed"]))
        tenure = int(rng.integers(0, 49))
        month = int(rng.integers(1, 13))
        persona = PersonaType.QCOMMERCE if int(rng.integers(0, 2)) == 1 else PersonaType.FOOD_DELIVERY

        target = float(
            np.clip(
                0.08
                + (0.28 * zone_base)
                + (0.22 * weather)
                + (0.18 * traffic)
                + (0.12 * incident)
                + (0.10 * historical)
                + (0.08 if persona == PersonaType.QCOMMERCE else 0.0),
                0.02,
                0.98,
            )
        )
        pred = risk_ml_service.predict_risk_score(
            zone_id="eval-zone",
            zone_base_risk=zone_base,
            weather_risk=weather,
            traffic_risk=traffic,
            incident_risk=incident,
            historical_risk=historical,
            persona=persona,
            age_band=age,
            vehicle_type=vehicle,
            shift_type=shift,
            tenure_months=tenure,
            month=month,
        )
        errors.append(abs(pred - target))

    mae = float(np.mean(errors))
    return {
        "mae": round(mae, 4),
        "threshold": 0.09,
        "pass": mae <= 0.09,
    }


def _eval_premium(samples: int = 1200) -> dict:
    rng = np.random.default_rng(1222)
    errors: list[float] = []
    for _ in range(samples):
        zone_factor = float(rng.uniform(0.8, 1.4))
        zone_base = float(rng.uniform(0.2, 0.85))
        risk_score = float(rng.uniform(0.05, 0.95))
        weather = float(rng.beta(1.8, 4.0))
        traffic = float(rng.beta(2.1, 2.8))
        incident = float(rng.beta(1.7, 3.8))
        historical = float(rng.beta(2.0, 5.2))
        month = int(rng.integers(1, 13))
        hour = int(rng.integers(0, 24))
        persona = PersonaType.QCOMMERCE if int(rng.integers(0, 2)) == 1 else PersonaType.FOOD_DELIVERY

        target = float(
            np.clip(
                0.88
                + (0.24 * risk_score)
                + (0.11 * weather)
                + (0.10 * traffic)
                + (0.10 * incident)
                + (0.05 * historical)
                + (0.07 if persona == PersonaType.QCOMMERCE else 0.0)
                + (0.09 * (zone_factor - 1.0)),
                0.75,
                1.85,
            )
        )
        pred = premium_ml_service.predict_weekly_multiplier(
            zone_id="eval-zone",
            zone_factor=zone_factor,
            zone_base_risk=zone_base,
            risk_score=risk_score,
            weather_risk=weather,
            traffic_risk=traffic,
            incident_risk=incident,
            historical_risk=historical,
            persona=persona,
            month=month,
            hour=hour,
        )
        errors.append(abs(pred - target))

    mae = float(np.mean(errors))
    return {
        "mae": round(mae, 4),
        "threshold": 0.08,
        "pass": mae <= 0.08,
    }


def _eval_fraud(samples: int = 1600) -> dict:
    rng = np.random.default_rng(1223)
    y_true: list[int] = []
    y_pred: list[int] = []
    probs: list[float] = []
    for _ in range(samples):
        features = {
            "location_fail": float(rng.binomial(1, 0.08)),
            "duplicate_fail": float(rng.binomial(1, 0.10)),
            "frequency_fail": float(rng.binomial(1, 0.16)),
            "trigger_fail": float(rng.binomial(1, 0.07)),
            "behavior_fail": float(rng.binomial(1, 0.15)),
            "distance_km": float(np.clip(rng.normal(2.4, 3.0), 0.0, 25.0)),
            "recent_same_claims": float(rng.integers(0, 5)),
            "claims_last_7_days": float(rng.integers(0, 8)),
            "anomaly_score": float(np.clip(rng.beta(2.0, 5.0), 0.0, 1.0)),
            "high_rejection_rate": float(rng.binomial(1, 0.12)),
            "same_hour_pattern": float(rng.binomial(1, 0.2)),
            "same_day_pattern": float(rng.binomial(1, 0.16)),
            "trigger_found": float(rng.binomial(1, 0.88)),
        }

        linear = (
            -2.8
            + features["location_fail"] * 1.2
            + features["duplicate_fail"] * 1.8
            + features["frequency_fail"] * 1.3
            + features["trigger_fail"] * 1.1
            + features["behavior_fail"] * 0.8
            + min(1.0, features["distance_km"] / 20.0) * 0.7
            + min(1.0, features["recent_same_claims"] / 4.0) * 1.0
            + min(1.0, features["claims_last_7_days"] / 7.0) * 0.9
            + features["anomaly_score"] * 1.2
            + features["high_rejection_rate"] * 1.0
            + features["same_hour_pattern"] * 0.4
            + features["same_day_pattern"] * 0.3
            + (1.0 - features["trigger_found"]) * 1.0
        )
        # Deterministic synthetic oracle label so evaluation measures model quality,
        # not irreducible Bernoulli sampling noise.
        p = float(1.0 / (1.0 + np.exp(-linear)))
        label = 1 if p >= 0.5 else 0

        pred_prob, _ = fraud_ml_service.predict_fraud_probability(features)
        pred = 1 if pred_prob >= 0.5 else 0

        y_true.append(label)
        y_pred.append(pred)
        probs.append(pred_prob)

    yt = np.array(y_true, dtype=int)
    yp = np.array(y_pred, dtype=int)
    tp = int(np.sum((yp == 1) & (yt == 1)))
    tn = int(np.sum((yp == 0) & (yt == 0)))
    fp = int(np.sum((yp == 1) & (yt == 0)))
    fn = int(np.sum((yp == 0) & (yt == 1)))
    accuracy = float(np.mean(yp == yt))
    precision = float(tp / max(1, (tp + fp)))
    recall = float(tp / max(1, (tp + fn)))
    f1 = float((2 * precision * recall) / max(1e-9, (precision + recall)))

    return {
        "accuracy": round(accuracy, 4),
        "f1": round(f1, 4),
        "thresholds": {"accuracy": 0.84, "f1": 0.78},
        "pass": accuracy >= 0.84 and f1 >= 0.78,
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "avg_predicted_probability": round(float(np.mean(probs)), 4),
    }


@router.get("/evaluate")
async def evaluate_ml_models(samples: int = 1200):
    samples = max(400, min(5000, int(samples)))
    risk_eval = _eval_risk(samples=samples)
    premium_eval = _eval_premium(samples=samples)
    fraud_eval = _eval_fraud(samples=max(800, int(samples * 1.2)))

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "sample_size": samples,
        "models": {
            "risk": {"version": risk_ml_service.model_version, **risk_eval},
            "premium": {"version": premium_ml_service.model_version, **premium_eval},
            "fraud": {"version": fraud_ml_service.model_version, **fraud_eval},
        },
        "overall_pass": risk_eval["pass"] and premium_eval["pass"] and fraud_eval["pass"],
        "note": "Evaluation uses synthetic holdout distributions aligned with in-repo training generators.",
    }
