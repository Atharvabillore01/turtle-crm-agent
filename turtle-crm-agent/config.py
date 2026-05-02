"""
Turtle CRM Agent Configuration
Loads settings from .env file via python-dotenv and uses dynamic paths
"""

import os
from dotenv import load_dotenv
from utils.path_utils import (
    get_output_path, get_data_path, get_log_path, 
    get_schema_path, ensure_path_exists
)

# Load environment variables
load_dotenv()

# ============================================================================
# LLM PROVIDER CONFIGURATION
# ============================================================================
# Choose LLM provider: 'anthropic', 'openai', or 'groq'
# Set via environment: export LLM_PROVIDER=openai
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()

# Validate provider
SUPPORTED_PROVIDERS = {'anthropic', 'claude', 'openai', 'azure', 'azure_openai', 'groq', 'gemini', 'google'}
if LLM_PROVIDER not in SUPPORTED_PROVIDERS:
    raise ValueError(
        f"Invalid LLM_PROVIDER: {LLM_PROVIDER}. "
        f"Supported: {', '.join(SUPPORTED_PROVIDERS)}"
    )

# Model configuration per provider
MODEL_CONFIG = {
    'anthropic': {
        'model': os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
        'api_key_var': 'ANTHROPIC_API_KEY',
    },
    'claude': {
        'model': os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
        'api_key_var': 'ANTHROPIC_API_KEY',
    },
    'openai': {
        'model': os.environ.get("OPENAI_MODEL", "gpt-4o"),
        'api_key_var': 'OPENAI_API_KEY',
    },
    'azure': {
        'model': os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1"),
        'api_key_var': 'AZURE_OPENAI_API_KEY',
    },
    'azure_openai': {
        'model': os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1"),
        'api_key_var': 'AZURE_OPENAI_API_KEY',
    },
    'groq': {
        'model': os.environ.get("GROQ_MODEL", "mixtral-8x7b-32768"),
        'api_key_var': 'GROQ_API_KEY',
    },
    'gemini': {
        'model': os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        'api_key_var': 'GEMINI_API_KEY',
    },
    'google': {
        'model': os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        'api_key_var': 'GEMINI_API_KEY',
    },
}

# Get API key for selected provider
PRIMARY_MODEL = MODEL_CONFIG[LLM_PROVIDER]['model']
API_KEY_VAR = MODEL_CONFIG[LLM_PROVIDER]['api_key_var']
API_KEY = os.environ.get(API_KEY_VAR)

if not API_KEY:
    import warnings
    warnings.warn(
        f"{API_KEY_VAR} not set. LLM calls will fail at runtime. "
        f"Set it: export {API_KEY_VAR}='your-key' (or add to .env)",
        RuntimeWarning,
        stacklevel=2,
    )

# Fallback model (only for Claude/Anthropic)
FALLBACK_MODEL = "claude-opus-4-7" if LLM_PROVIDER in ('anthropic', 'claude') else None

# ============================================================================
# PROCESSING CONFIGURATION
# ============================================================================
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.70"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
MAX_TRANSCRIPT_CHARS = int(os.environ.get("MAX_TRANSCRIPT_CHARS", "60000"))

# Dynamic paths - use environment variables or defaults
OUTPUT_DIR = ensure_path_exists(
    os.environ.get("OUTPUT_DIR", get_output_path()), is_dir=True
)
DATA_DIR = get_data_path()  # data/conversations

# Maximum context size (stay below 180K to be safe)
MAX_CONTEXT_TOKENS = 180000

# Input file validation
ALLOWED_EXTENSIONS = {'.md', '.pdf', '.xlsx', '.xls', '.csv', '.txt'}
MAX_FILE_SIZE_MB = 50

# ============================================================================
# FIELD SCHEMA
# ============================================================================
SCHEMA_PATH = get_schema_path("crm_schema.json")

# 30 Priority Fields (Phase 1)
PRIORITY_FIELDS = [
    2, 6, 9, 10, 11, 13, 14, 17, 31, 36, 37, 38, 39, 43, 47, 49, 
    60, 65, 68, 79, 80, 82, 83, 84, 86, 87, 98, 106, 108, 113, 144, 145, 146
]

# ============================================================================
# VALIDATION & CONFIDENCE RULES
# ============================================================================
REVIEW_THRESHOLD = CONFIDENCE_THRESHOLD  # 0.70 default

# Confidence score mapping
CONFIDENCE_RANGES = {
    "exact_quote": (0.90, 0.99),           # Explicit statement in transcript
    "clearly_inferable": (0.70, 0.89),     # Clear from context
    "estimated": (0.50, 0.69),             # Approximate or range
    "indirect": (0.30, 0.49),              # Inferred from lifestyle/behavior
    "speculative": (0.00, 0.29),           # Not mentioned / low confidence
}

# ============================================================================
# SECURITY
# ============================================================================
# PII masking patterns are defined in security/pii_guard.py
# Import PII_PATTERNS from there if needed:
# from security.pii_guard import PII_PATTERNS

# ============================================================================
# AUDIT & LOGGING
# ============================================================================
AUDIT_LOG_DIR = ensure_path_exists(get_log_path('audit'), is_dir=True)
DEBUG_LOGS_DIR = ensure_path_exists(get_log_path('debug'), is_dir=True)

# Never log these values (even if masked)
SENSITIVE_FIELDS = {'ANTHROPIC_API_KEY', 'password', 'credential'}

# ============================================================================
# AGENT EXECUTION ORDER
# ============================================================================
AGENT_EXECUTION_ORDER = [
    'demographics',
    'finance',
    'schedule',
    'qualitative',
    'task',      # depends on previous results
    'feedback',
    'system_resolver',
]
