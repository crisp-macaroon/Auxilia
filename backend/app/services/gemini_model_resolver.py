"""Helpers to resolve an available Gemini model for generateContent."""

from __future__ import annotations

import logging
from typing import Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

_PREFERRED_MODEL_PREFIXES = [
    "models/gemini-2.0-flash",
    "models/gemini-1.5-flash",
    "models/gemini-1.5-flash-8b",
    "models/gemini-1.5-pro",
    "models/gemini-pro",
]


def resolve_generate_model_name(default: str = "gemini-1.5-flash") -> str:
    """
    Resolve a model that supports generateContent for the current key.
    Falls back to provided default when listing is unavailable.
    """
    try:
        models = list(genai.list_models())
    except Exception as exc:
        logger.warning("Could not list Gemini models, using default '%s': %s", default, exc)
        return default

    supported = []
    for model in models:
        methods = getattr(model, "supported_generation_methods", None) or []
        if "generateContent" in methods:
            name = getattr(model, "name", "")
            if name:
                supported.append(name)

    if not supported:
        logger.warning("No generateContent Gemini model listed, using default '%s'", default)
        return default

    for preferred in _PREFERRED_MODEL_PREFIXES:
        for available in supported:
            if available.startswith(preferred):
                return available

    return supported[0]


def build_model(model_name: str):
    """Build Gemini model object from resolved name."""
    return genai.GenerativeModel(model_name)
