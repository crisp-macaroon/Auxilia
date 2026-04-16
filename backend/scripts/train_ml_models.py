"""
Train and persist ML models used by Auxilia backend.

Usage:
    python scripts/train_ml_models.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.ml_service import FraudModelService, PremiumModelService, RiskModelService


def main() -> None:
    artifact_dir = ROOT / "ml"
    risk = RiskModelService(artifact_dir)
    premium = PremiumModelService(artifact_dir)
    fraud = FraudModelService(artifact_dir)

    risk.train_and_save(samples=15_000)
    premium.train_and_save(samples=18_000)
    fraud.train_and_save(samples=16_000)

    print("Risk model:", risk.model_version, "->", artifact_dir / "risk_model.pkl")
    print("Premium model:", premium.model_version, "->", artifact_dir / "premium_model.pkl")
    print("Fraud model:", fraud.model_version, "->", artifact_dir / "fraud_model.pkl")


if __name__ == "__main__":
    main()
