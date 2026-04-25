"""
Gemini-powered payout advisory service.
Provides explainable guidance while final payout remains rule-governed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

import google.generativeai as genai

from app.core.config import settings
from app.services.gemini_model_resolver import resolve_generate_model_name, build_model

logger = logging.getLogger(__name__)


class PayoutAdvisoryService:
    """Generate non-binding payout advice using Gemini."""

    def __init__(self) -> None:
        self._enabled = bool(settings.GEMINI_API_KEY)
        self._model = None
        self._model_name = ""
        self._model_refresh_attempted = False
        self._disabled_until: datetime | None = None

        if not self._enabled:
            logger.info("Gemini advisory disabled: GEMINI_API_KEY not set")
            return

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model_name = resolve_generate_model_name(default="gemini-1.5-flash")
            self._model = build_model(self._model_name)
            logger.info("Gemini payout advisory model selected: %s", self._model_name)
        except Exception as exc:
            logger.error("Failed to initialize Gemini payout advisory model: %s", exc)
            self._enabled = False
            self._model = None

    async def get_payout_advisory(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return advisory as:
        {
          recommendation: approve|reject|manual_review,
          confidence: float 0..1,
          rationale: str,
          key_risks: [str]
        }
        """
        if self._disabled_until and datetime.utcnow() < self._disabled_until:
            return {
                "recommendation": "manual_review",
                "confidence": 0.0,
                "rationale": "Gemini advisory temporarily paused after API quota/rate-limit errors.",
                "key_risks": ["llm_temporarily_disabled"],
            }

        if not self._enabled or self._model is None:
            return {
                "recommendation": "manual_review",
                "confidence": 0.0,
                "rationale": "Gemini advisory unavailable; using deterministic payout rules.",
                "key_risks": ["llm_unavailable"],
            }

        prompt = self._build_prompt(context)
        try:
            raw = await asyncio.to_thread(self._model.generate_content, prompt)
            parsed = self._parse_json(raw.text if hasattr(raw, "text") else "")
            return {
                "recommendation": str(parsed.get("recommendation", "manual_review")).lower(),
                "confidence": float(parsed.get("confidence", 0.0) or 0.0),
                "rationale": str(parsed.get("rationale", "No rationale provided")).strip(),
                "key_risks": [str(r).strip() for r in (parsed.get("key_risks") or []) if str(r).strip()],
            }
        except Exception as exc:
            text = str(exc).lower()

            if ("not found" in text or "not supported" in text) and not self._model_refresh_attempted:
                self._model_refresh_attempted = True
                try:
                    refreshed = resolve_generate_model_name(default="gemini-2.0-flash")
                    if refreshed != self._model_name:
                        self._model_name = refreshed
                        self._model = build_model(self._model_name)
                        logger.info("Gemini payout advisory switched model to: %s", self._model_name)
                        raw = await asyncio.to_thread(self._model.generate_content, prompt)
                        parsed = self._parse_json(raw.text if hasattr(raw, "text") else "")
                        return {
                            "recommendation": str(parsed.get("recommendation", "manual_review")).lower(),
                            "confidence": float(parsed.get("confidence", 0.0) or 0.0),
                            "rationale": str(parsed.get("rationale", "No rationale provided")).strip(),
                            "key_risks": [str(r).strip() for r in (parsed.get("key_risks") or []) if str(r).strip()],
                        }
                except Exception as retry_exc:
                    logger.warning("Gemini payout advisory retry failed: %s", retry_exc)

            if any(marker in text for marker in ["resourceexhausted", "quota", "rate limit", "429"]):
                self._disabled_until = datetime.utcnow() + timedelta(minutes=5)

            logger.warning("Gemini payout advisory failed: %s", exc)
            return {
                "recommendation": "manual_review",
                "confidence": 0.0,
                "rationale": "Gemini advisory request failed; fallback to deterministic payout rules.",
                "key_risks": ["llm_request_failed"],
            }

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        return (
            "You are an insurance payout advisory assistant for parametric gig-worker claims. "
            "Output STRICT JSON only with keys: recommendation, confidence, rationale, key_risks. "
            "recommendation must be one of approve|reject|manual_review. "
            "confidence is a float from 0 to 1. key_risks is an array of short strings. "
            "Do NOT include markdown. Do NOT include extra keys.\n\n"
            f"Claim context:\n{json.dumps(context, ensure_ascii=True)}"
        )

    def _parse_json(self, text: str) -> Dict[str, Any]:
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini advisory response is not a JSON object")
        return parsed


payout_advisory_service = PayoutAdvisoryService()
