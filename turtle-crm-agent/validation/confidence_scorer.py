"""
Confidence Scorer - Assigns confidence scores to extracted fields
"""

from typing import Dict, Any


CONFIDENCE_RANGES = {
    "exact_quote": (0.90, 0.99),           # Explicit statement
    "clearly_inferable": (0.70, 0.89),     # Clear from context
    "estimated": (0.50, 0.69),             # Approximate/range
    "indirect": (0.30, 0.49),              # Inferred
    "speculative": (0.00, 0.29),           # Speculative/guessed
}

REVIEW_THRESHOLD = 0.70


def score_field(
    value: Any,
    confidence_level: str = "estimated",
    boost: float = 0.0
) -> float:
    """
    Assign confidence score to extracted field.
    
    Args:
        value: Extracted value (None if not found)
        confidence_level: Confidence category key
        boost: Additional confidence boost (0.0-0.1)
        
    Returns:
        Confidence score 0.0-1.0
    """
    if value is None:
        return 0.0
    
    if confidence_level not in CONFIDENCE_RANGES:
        confidence_level = "estimated"
    
    min_conf, max_conf = CONFIDENCE_RANGES[confidence_level]
    base_score = (min_conf + max_conf) / 2
    
    # Apply boost (capped at range max)
    final_score = min(base_score + boost, max_conf)
    
    return round(final_score, 2)


def should_flag_for_review(confidence: float) -> bool:
    """
    Determine if field should be flagged for human review.
    
    Args:
        confidence: Confidence score 0.0-1.0
        
    Returns:
        True if below review threshold
    """
    return confidence < REVIEW_THRESHOLD


def score_multiple_mentions(
    base_score: float,
    mention_count: int
) -> float:
    """
    Boost confidence when field mentioned multiple times.
    
    Args:
        base_score: Initial confidence
        mention_count: Number of mentions across calls
        
    Returns:
        Boosted confidence score
    """
    boost = min((mention_count - 1) * 0.05, 0.10)  # Max +0.10
    return min(base_score + boost, 1.0)
