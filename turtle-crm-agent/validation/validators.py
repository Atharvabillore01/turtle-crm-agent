"""
Validators - Field validation rules
Ensures extracted data conforms to schema requirements.
"""

import re
from typing import Any, Callable, Dict, Tuple


VALIDATORS: Dict[str, Callable[[Any], bool]] = {
    # Enums
    "gender": lambda v: v in ("M", "F", "O", None),
    "marital_status": lambda v: v in ("Single", "Married", "Divorced", "Widowed", None),
    "attitude": lambda v: v in ("Optimistic", "Pessimistic", "Critical", "Neutral", None),
    "acumen": lambda v: v in ("H", "M", "L", None),
    "relevance": lambda v: v in ("H", "M", "L", None),
    "complexity": lambda v: v in ("H", "M", "L", None),
    "exec_capability": lambda v: v in ("H", "M", "L", None),
    "tech_savvy": lambda v: v in ("H", "M", "L", None),
    "sentiment": lambda v: v in ("Positive", "Neutral", "Negative", "Mixed", None),
    "rpa": lambda v: v in ("Aggressive", "Moderate", "Conservative", None),
    "employment_type": lambda v: v in ("Salaried", "Self Employed", "On a break", "NA", None),
    "will_executed": lambda v: v in ("Y", "N", None),
    
    # Numeric
    "currency": lambda v: v is None or (isinstance(v, (int, float)) and v >= 0),
    "integer_positive": lambda v: v is None or (isinstance(v, int) and v >= 0),
    "kids_count": lambda v: v is None or (isinstance(v, int) and 0 <= v <= 20),
    
    # Text format
    "email": lambda v: v is None or bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', v)),
    "phone": lambda v: v is None or bool(re.match(r'^\+?[0-9]{7,15}$', str(v).replace(' ', ''))),
    "pan": lambda v: v is None or bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', v)),
    
    # Date
    "date_iso": lambda v: v is None or bool(re.match(r'^\d{4}-\d{2}-\d{2}$', v)),
    
    # List/Array
    "list": lambda v: v is None or isinstance(v, list),
    "string_or_list": lambda v: v is None or isinstance(v, (str, list)),
}


def validate_field(value: Any, validator_type: str) -> Tuple[bool, str]:
    """
    Validate a field value against a validator type.
    
    Args:
        value: Value to validate
        validator_type: Type of validator to apply
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if validator_type not in VALIDATORS:
        return False, f"Unknown validator type: {validator_type}"
    
    validator = VALIDATORS[validator_type]
    
    try:
        if validator(value):
            return True, ""
        else:
            return False, f"Value {value} failed {validator_type} validation"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_enum(value: Any, allowed_values: list) -> Tuple[bool, str]:
    """
    Validate that value is in allowed enum values.
    
    Args:
        value: Value to check
        allowed_values: List of allowed values
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return True, ""
    
    if value in allowed_values:
        return True, ""
    
    return False, f"Value '{value}' not in allowed values: {allowed_values}"


def validate_range(value: Any, min_val: float = None, max_val: float = None) -> Tuple[bool, str]:
    """
    Validate that value is within a range.
    
    Args:
        value: Numeric value to check
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return True, ""
    
    if not isinstance(value, (int, float)):
        return False, f"Value must be numeric, got {type(value)}"
    
    if min_val is not None and value < min_val:
        return False, f"Value {value} is below minimum {min_val}"
    
    if max_val is not None and value > max_val:
        return False, f"Value {value} is above maximum {max_val}"
    
    return True, ""
