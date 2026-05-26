"""
Confidence Scorer - Assigns confidence scores to extracted fields.
Single source of truth for scores is config.CONFIDENCE_SCORES.
"""

from typing import Any
from config import CONFIDENCE_SCORES, CONFIDENCE_THRESHOLD


def score_field(value: Any, confidence_level: str = "estimated", boost: float = 0.0) -> float:
    """
    Return numeric confidence for a field.

    Args:
        value: Extracted value — None returns 0.0 immediately
        confidence_level: Label from LLM (exact_quote, clearly_inferable, …)
        boost: Small additive boost (capped at 0.99)

    Returns:
        Score 0.0 – 1.0
    """
    if value is None:
        return 0.0
    base = CONFIDENCE_SCORES.get(confidence_level, CONFIDENCE_SCORES["estimated"])
    return round(min(base + boost, 0.99), 2)


def should_flag_for_review(confidence: float) -> bool:
    """True when confidence is below the configured review threshold."""
    return confidence < CONFIDENCE_THRESHOLD


def score_multiple_mentions(base_score: float, mention_count: int) -> float:
    """Boost confidence when a field is mentioned multiple times (max +0.10)."""
    boost = min((mention_count - 1) * 0.05, 0.10)
    return round(min(base_score + boost, 1.0), 2)
