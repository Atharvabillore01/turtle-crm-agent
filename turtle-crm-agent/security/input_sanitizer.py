"""
Input Sanitizer - Pre-parsing validation
Validates files before any parsing occurs.
"""

from pathlib import Path
from typing import List

from config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB


def validate_file(filepath: str) -> bool:
    """
    Validate file before passing to any parser.
    
    Args:
        filepath: Path to file to validate
        
    Returns:
        True if valid, raises ValueError if invalid
        
    Raises:
        ValueError: If file is invalid
    """
    path = Path(filepath)
    
    # Check file exists
    if not path.exists():
        raise ValueError(f"File not found: {filepath}")
    
    # Check extension
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.suffix}. Allowed: {ALLOWED_EXTENSIONS}")
    
    # Check file size
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)")
    
    return True


def validate_files(filepaths: List[str]) -> bool:
    """
    Validate a list of files.
    
    Args:
        filepaths: List of file paths
        
    Returns:
        True if all valid
        
    Raises:
        ValueError: If any file is invalid
    """
    for filepath in filepaths:
        validate_file(filepath)
    
    return True
