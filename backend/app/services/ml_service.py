"""
ML model services for risk scoring and premium prediction.

These services provide real model-backed inference and auto-train
baseline models when artifacts are missing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor

from app.models.schemas import PersonaType


AGE_BAND_ENC = {
    "18-21": 0.20,
    "22-25": 0.35,
    "26-35": 0.55,
    "36-45": 0.70,
    "46+": 0.85,
}

VEHICLE_ENC = {
    "bike": 0.85,
    "scooter": 0.60,
    "ev_scooter": 0.65,
    "bicycle": 0.35,
}

SHIFT_ENC = {
    "breakfast": 0.30,
    "lunch": 0.45,
    "evening": 0.70,
    "late_night": 0.95,
    "mixed": 0.60,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _zone_hash_feature(zone_id: str) -> float:
    digest = sha1(zone_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 10_000
    return bucket / 10_000.0


def _persona_to_num(persona: PersonaType) -> float:
    return 1.0 if persona == PersonaType.QCOMMERCE else 0.0


def _age_to_num(age_band: str | None) -> float:
    return AGE_BAND_ENC.get((age_band or "").lower(), 0.5)


def _vehicle_to_num(vehicle_type: str | None) -> float:
    return VEHICLE_ENC.get((vehicle_type or "").lower(), 0.6)


def _shift_to_num(shift_type: str | None) -> float:
    return SHIFT_ENC.get((shift_type or "").lower(), 0.55)


def _tenure_to_num(tenure_months: int | None) -> float:
    tenure = max(0, int(tenure_months or 0))
    return _clamp(tenure / 48.0, 0.0, 1.0)


@dataclass
class ModelInfo:
    model_name: str
    version: str
    trained_at: str
    train_rows: int
    feature_names: list[str]


class RiskModelService:
    def __init__(self, artifact_dir: Path):
        self._artifact_dir = artifact_dir
        self._model_path = artifact_dir / "risk_model.pkl"
        self._meta_path = artifact_dir / "risk_model_meta.json"
        self._model: GradientBoostingRegressor | None = None
        self._meta: ModelInfo | None = None
        self._feature_names = [
            "zone_hash",
            "zone_base_risk",
            "weather_risk",
            "traffic_risk",
            "incident_risk",
            "historical_risk",
            "persona_num",
            "age_num",
            "vehicle_num",
            "shift_num",
            "tenure_num",
            "month_sin",
            "month_cos",
        ]
        self._ensure_loaded()

    @property
    def model_version(self) -> str:
        return self._meta.version if self._meta else "risk-gbm-v1"

    def _ensure_loaded(self) -> None:
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        if self._model_path.exists() and self._meta_path.exists():
            self._model = joblib.load(self._model_path)
            self._meta = ModelInfo(**json.loads(self._meta_path.read_text(encoding="utf-8")))
            return
        self.train_and_save()

    def train_and_save(self, samples: int = 12_000) -> None:
        rng = np.random.default_rng(42)

        zone_hash = rng.random(samples)
        zone_base_risk = rng.uniform(0.2, 0.85, samples)
        weather_risk = rng.beta(1.8, 4.2, samples)
        traffic_risk = rng.beta(2.2, 2.7, samples)
        incident_risk = rng.beta(1.6, 3.8, samples)
        historical_risk = rng.beta(2.0, 5.0, samples)
        persona_num = rng.integers(0, 2, samples)
        age_num = rng.uniform(0.2, 0.9, samples)
        vehicle_num = rng.uniform(0.3, 0.9, samples)
        shift_num = rng.uniform(0.25, 0.98, samples)
        tenure_num = rng.uniform(0.0, 1.0, samples)
        month = rng.integers(1, 13, samples)
        month_sin = np.sin((2 * np.pi * month) / 12)
        month_cos = np.cos((2 * np.pi * month) / 12)

        linear = (
            0.08
            + (0.28 * zone_base_risk)
            + (0.22 * weather_risk)
            + (0.18 * traffic_risk)
            + (0.12 * incident_risk)
            + (0.10 * historical_risk)
            + (0.07 * persona_num)
            + (0.04 * age_num)
            + (0.05 * vehicle_num)
            + (0.07 * shift_num)
            - (0.05 * tenure_num)
            + (0.03 * zone_hash)
            + (0.02 * month_sin)
        )
        nonlinear = (weather_risk * traffic_risk * 0.09) + (incident_risk * shift_num * 0.06)
        noise = rng.normal(0.0, 0.025, samples)
        y = np.clip(linear + nonlinear + noise, 0.02, 0.98)

        X = np.column_stack(
            [
                zone_hash,
                zone_base_risk,
                weather_risk,
                traffic_risk,
                incident_risk,
                historical_risk,
                persona_num,
                age_num,
                vehicle_num,
                shift_num,
                tenure_num,
                month_sin,
                month_cos,
            ]
        )

        model = GradientBoostingRegressor(
            random_state=42,
            n_estimators=420,
            max_depth=3,
            learning_rate=0.04,
            min_samples_leaf=10,
            subsample=0.9,
        )
        model.fit(X, y)

        meta = ModelInfo(
            model_name="risk-gradient-boosting",
            version="risk-gbm-v1",
            trained_at=datetime.utcnow().isoformat(),
            train_rows=samples,
            feature_names=self._feature_names,
        )

        joblib.dump(model, self._model_path)
        self._meta_path.write_text(json.dumps(meta.__dict__, indent=2), encoding="utf-8")

        self._model = model
        self._meta = meta

    def _feature_vector(
        self,
        *,
        zone_id: str,
        zone_base_risk: float,
        weather_risk: float,
        traffic_risk: float,
        incident_risk: float,
        historical_risk: float,
        persona: PersonaType,
        age_band: str | None,
        vehicle_type: str | None,
        shift_type: str | None,
        tenure_months: int | None,
        month: int,
    ) -> np.ndarray:
        month_sin = np.sin((2 * np.pi * month) / 12)
        month_cos = np.cos((2 * np.pi * month) / 12)
        return np.array(
            [
                _zone_hash_feature(zone_id),
                _clamp(zone_base_risk, 0.0, 1.0),
                _clamp(weather_risk, 0.0, 1.0),
                _clamp(traffic_risk, 0.0, 1.0),
                _clamp(incident_risk, 0.0, 1.0),
                _clamp(historical_risk, 0.0, 1.0),
                _persona_to_num(persona),
                _age_to_num(age_band),
                _vehicle_to_num(vehicle_type),
                _shift_to_num(shift_type),
                _tenure_to_num(tenure_months),
                month_sin,
                month_cos,
            ],
            dtype=float,
        )

    def predict_risk_score(
        self,
        *,
        zone_id: str,
        zone_base_risk: float,
        weather_risk: float,
        traffic_risk: float,
        incident_risk: float,
        historical_risk: float,
        persona: PersonaType,
        age_band: str | None,
        vehicle_type: str | None,
        shift_type: str | None,
        tenure_months: int | None,
        month: int,
    ) -> float:
        if self._model is None:
            self._ensure_loaded()
        features = self._feature_vector(
            zone_id=zone_id,
            zone_base_risk=zone_base_risk,
            weather_risk=weather_risk,
            traffic_risk=traffic_risk,
            incident_risk=incident_risk,
            historical_risk=historical_risk,
            persona=persona,
            age_band=age_band,
            vehicle_type=vehicle_type,
            shift_type=shift_type,
            tenure_months=tenure_months,
            month=month,
        )
        pred = float(self._model.predict([features])[0])
        return _clamp(pred, 0.01, 0.99)


class PremiumModelService:
    def __init__(self, artifact_dir: Path):
        self._artifact_dir = artifact_dir
        self._model_path = artifact_dir / "premium_model.pkl"
        self._meta_path = artifact_dir / "premium_model_meta.json"
        self._model: RandomForestRegressor | None = None
        self._meta: ModelInfo | None = None
        self._feature_names = [
            "zone_hash",
            "zone_factor",
            "zone_base_risk",
            "risk_score",
            "weather_risk",
            "traffic_risk",
            "incident_risk",
            "historical_risk",
            "persona_num",
            "month_sin",
            "month_cos",
            "hour_sin",
            "hour_cos",
        ]
        self._ensure_loaded()

    @property
    def model_version(self) -> str:
        return self._meta.version if self._meta else "premium-rf-v1"

    def _ensure_loaded(self) -> None:
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        if self._model_path.exists() and self._meta_path.exists():
            self._model = joblib.load(self._model_path)
            self._meta = ModelInfo(**json.loads(self._meta_path.read_text(encoding="utf-8")))
            return
        self.train_and_save()

    def train_and_save(self, samples: int = 15_000) -> None:
        rng = np.random.default_rng(43)

        zone_hash = rng.random(samples)
        zone_factor = rng.uniform(0.8, 1.4, samples)
        zone_base_risk = rng.uniform(0.2, 0.85, samples)
        risk_score = rng.uniform(0.05, 0.95, samples)
        weather_risk = rng.beta(1.8, 4.0, samples)
        traffic_risk = rng.beta(2.1, 2.8, samples)
        incident_risk = rng.beta(1.7, 3.8, samples)
        historical_risk = rng.beta(2.0, 5.2, samples)
        persona_num = rng.integers(0, 2, samples)
        month = rng.integers(1, 13, samples)
        hour = rng.integers(0, 24, samples)

        month_sin = np.sin((2 * np.pi * month) / 12)
        month_cos = np.cos((2 * np.pi * month) / 12)
        hour_sin = np.sin((2 * np.pi * hour) / 24)
        hour_cos = np.cos((2 * np.pi * hour) / 24)

        base = (
            0.88
            + (0.24 * risk_score)
            + (0.11 * weather_risk)
            + (0.10 * traffic_risk)
            + (0.10 * incident_risk)
            + (0.05 * historical_risk)
            + (0.07 * persona_num)
            + (0.09 * (zone_factor - 1.0))
            + (0.05 * zone_base_risk)
            + (0.03 * zone_hash)
            + (0.03 * month_sin)
            + (0.02 * hour_sin)
        )
        nonlinear = (weather_risk * traffic_risk * 0.10) + (incident_risk * risk_score * 0.09)
        noise = rng.normal(0.0, 0.03, samples)
        y = np.clip(base + nonlinear + noise, 0.75, 1.85)

        X = np.column_stack(
            [
                zone_hash,
                zone_factor,
                zone_base_risk,
                risk_score,
                weather_risk,
                traffic_risk,
                incident_risk,
                historical_risk,
                persona_num,
                month_sin,
                month_cos,
                hour_sin,
                hour_cos,
            ]
        )

        model = RandomForestRegressor(
            random_state=43,
            n_estimators=320,
            max_depth=14,
            min_samples_leaf=8,
            n_jobs=-1,
        )
        model.fit(X, y)

        meta = ModelInfo(
            model_name="premium-random-forest",
            version="premium-rf-v1",
            trained_at=datetime.utcnow().isoformat(),
            train_rows=samples,
            feature_names=self._feature_names,
        )

        joblib.dump(model, self._model_path)
        self._meta_path.write_text(json.dumps(meta.__dict__, indent=2), encoding="utf-8")

        self._model = model
        self._meta = meta

    def predict_weekly_multiplier(
        self,
        *,
        zone_id: str,
        zone_factor: float,
        zone_base_risk: float,
        risk_score: float,
        weather_risk: float,
        traffic_risk: float,
        incident_risk: float,
        historical_risk: float,
        persona: PersonaType,
        month: int,
        hour: int,
    ) -> float:
        if self._model is None:
            self._ensure_loaded()

        month_sin = np.sin((2 * np.pi * month) / 12)
        month_cos = np.cos((2 * np.pi * month) / 12)
        hour_sin = np.sin((2 * np.pi * hour) / 24)
        hour_cos = np.cos((2 * np.pi * hour) / 24)

        features = np.array(
            [
                _zone_hash_feature(zone_id),
                _clamp(zone_factor, 0.7, 1.6),
                _clamp(zone_base_risk, 0.0, 1.0),
                _clamp(risk_score, 0.0, 1.0),
                _clamp(weather_risk, 0.0, 1.0),
                _clamp(traffic_risk, 0.0, 1.0),
                _clamp(incident_risk, 0.0, 1.0),
                _clamp(historical_risk, 0.0, 1.0),
                _persona_to_num(persona),
                month_sin,
                month_cos,
                hour_sin,
                hour_cos,
            ],
            dtype=float,
        )

        pred = float(self._model.predict([features])[0])
        return _clamp(pred, 0.75, 1.85)


class FraudModelService:
    def __init__(self, artifact_dir: Path):
        self._artifact_dir = artifact_dir
        self._model_path = artifact_dir / "fraud_model.pkl"
        self._meta_path = artifact_dir / "fraud_model_meta.json"
        self._model: RandomForestClassifier | None = None
        self._meta: ModelInfo | None = None
        self._feature_names = [
            "location_fail",
            "duplicate_fail",
            "frequency_fail",
            "trigger_fail",
            "behavior_fail",
            "distance_km",
            "recent_same_claims",
            "claims_last_7_days",
            "anomaly_score",
            "high_rejection_rate",
            "same_hour_pattern",
            "same_day_pattern",
            "trigger_found",
        ]
        self._ensure_loaded()

    @property
    def model_version(self) -> str:
        return self._meta.version if self._meta else "fraud-rf-v1"

    def _ensure_loaded(self) -> None:
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        if self._model_path.exists() and self._meta_path.exists():
            self._model = joblib.load(self._model_path)
            self._meta = ModelInfo(**json.loads(self._meta_path.read_text(encoding="utf-8")))
            return
        self.train_and_save()

    def train_and_save(self, samples: int = 14_000) -> None:
        rng = np.random.default_rng(44)

        location_fail = rng.binomial(1, 0.08, samples)
        duplicate_fail = rng.binomial(1, 0.10, samples)
        frequency_fail = rng.binomial(1, 0.16, samples)
        trigger_fail = rng.binomial(1, 0.07, samples)
        behavior_fail = rng.binomial(1, 0.15, samples)

        distance_km = np.clip(rng.normal(2.4, 3.0, samples), 0.0, 25.0)
        recent_same_claims = rng.integers(0, 5, samples)
        claims_last_7_days = rng.integers(0, 8, samples)
        anomaly_score = np.clip(rng.beta(2.0, 5.0, samples), 0.0, 1.0)
        high_rejection_rate = rng.binomial(1, 0.12, samples)
        same_hour_pattern = rng.binomial(1, 0.2, samples)
        same_day_pattern = rng.binomial(1, 0.16, samples)
        trigger_found = rng.binomial(1, 0.88, samples)

        linear = (
            -2.8
            + location_fail * 1.2
            + duplicate_fail * 1.8
            + frequency_fail * 1.3
            + trigger_fail * 1.1
            + behavior_fail * 0.8
            + np.clip(distance_km / 20.0, 0.0, 1.0) * 0.7
            + np.clip(recent_same_claims / 4.0, 0.0, 1.0) * 1.0
            + np.clip(claims_last_7_days / 7.0, 0.0, 1.0) * 0.9
            + anomaly_score * 1.2
            + high_rejection_rate * 1.0
            + same_hour_pattern * 0.4
            + same_day_pattern * 0.3
            + (1 - trigger_found) * 1.0
        )
        prob = 1.0 / (1.0 + np.exp(-linear))
        y = (rng.random(samples) < prob).astype(int)

        X = np.column_stack(
            [
                location_fail,
                duplicate_fail,
                frequency_fail,
                trigger_fail,
                behavior_fail,
                distance_km,
                recent_same_claims,
                claims_last_7_days,
                anomaly_score,
                high_rejection_rate,
                same_hour_pattern,
                same_day_pattern,
                trigger_found,
            ]
        )

        model = RandomForestClassifier(
            random_state=44,
            n_estimators=420,
            max_depth=14,
            min_samples_leaf=8,
            n_jobs=-1,
            class_weight=None,
        )
        model.fit(X, y)

        meta = ModelInfo(
            model_name="fraud-random-forest-classifier",
            version="fraud-rf-v1",
            trained_at=datetime.utcnow().isoformat(),
            train_rows=samples,
            feature_names=self._feature_names,
        )
        joblib.dump(model, self._model_path)
        self._meta_path.write_text(json.dumps(meta.__dict__, indent=2), encoding="utf-8")

        self._model = model
        self._meta = meta

    def predict_fraud_probability(self, features: dict[str, float]) -> tuple[float, float]:
        if self._model is None:
            self._ensure_loaded()

        vector = np.array(
            [
                float(features.get("location_fail", 0.0)),
                float(features.get("duplicate_fail", 0.0)),
                float(features.get("frequency_fail", 0.0)),
                float(features.get("trigger_fail", 0.0)),
                float(features.get("behavior_fail", 0.0)),
                _clamp(float(features.get("distance_km", 0.0)), 0.0, 25.0),
                _clamp(float(features.get("recent_same_claims", 0.0)), 0.0, 10.0),
                _clamp(float(features.get("claims_last_7_days", 0.0)), 0.0, 20.0),
                _clamp(float(features.get("anomaly_score", 0.0)), 0.0, 1.0),
                float(features.get("high_rejection_rate", 0.0)),
                float(features.get("same_hour_pattern", 0.0)),
                float(features.get("same_day_pattern", 0.0)),
                float(features.get("trigger_found", 1.0)),
            ],
            dtype=float,
        )

        proba = self._model.predict_proba([vector])[0]
        fraud_prob = float(proba[1])
        confidence = float(abs(proba[1] - proba[0]))
        return _clamp(fraud_prob, 0.0, 1.0), _clamp(confidence, 0.0, 1.0)


_artifact_root = Path(__file__).resolve().parents[2] / "ml"
risk_ml_service = RiskModelService(_artifact_root)
premium_ml_service = PremiumModelService(_artifact_root)
fraud_ml_service = FraudModelService(_artifact_root)
