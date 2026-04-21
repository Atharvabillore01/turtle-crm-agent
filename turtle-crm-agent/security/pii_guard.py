"""
PII Guard - Security Module
Masks and redacts personally identifiable information before logging.
"""

import re
from typing import Dict, Pattern

# Compiled regex patterns for PII detection
PII_PATTERNS: Dict[str, Pattern] = {
    'pan': re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]'),
    'aadhaar': re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b'),
    'phone_india': re.compile(r'\b[6-9]\d{9}\b'),
    'phone_us': re.compile(r'\b\+?1?\s?\(?\d{3}\)?\s?[-.]?\d{3}[-.]?\d{4}\b'),
    'email': re.compile(r'[\w\.-]+@[\w\.-]+\.\w{2,}'),
    'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    'account_num': re.compile(r'\b\d{8,17}\b'),
    'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
}


def mask_pii(text: str) -> str:
    """
    Replace all detected PII in text with redaction markers.
    
    Args:
        text: Text that may contain PII
        
    Returns:
        Text with PII redacted
    """
    if not text:
        return text
    
    for label, pattern in PII_PATTERNS.items():
        text = pattern.sub(f'[{label.upper()}_REDACTED]', text)
    
    return text


def mask_pii_dict(data: dict) -> dict:
    """
    Recursively mask PII in a dictionary.
    
    Args:
        data: Dictionary that may contain PII values
        
    Returns:
        Dictionary with PII values redacted
    """
    if not isinstance(data, dict):
        return data
    
    masked = {}
    for key, value in data.items():
        if isinstance(value, str):
            masked[key] = mask_pii(value)
        elif isinstance(value, dict):
            masked[key] = mask_pii_dict(value)
        elif isinstance(value, list):
            masked[key] = [mask_pii(item) if isinstance(item, str) else item for item in value]
        else:
            masked[key] = value
    
    return masked


def safe_log(logger, level: str, message: str) -> None:
    """
    Log a message with PII safely redacted.
    
    Args:
        logger: Python logger instance
        level: Log level ('debug', 'info', 'warning', 'error')
        message: Message to log
    """
    safe_message = mask_pii(message)
    getattr(logger, level)(safe_message)


def extract_sensitive_patterns(text: str) -> Dict[str, list]:
    """
    Find all PII matches in text without returning the actual values.
    Useful for auditing what PII was found.
    
    Args:
        text: Text to scan for PII
        
    Returns:
        Dictionary mapping PII type to count of occurrences
    """
    if not text:
        return {}
    
    findings = {}
    for label, pattern in PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            findings[label] = len(matches)
    
    return findings
