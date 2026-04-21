"""
Path Utilities - Project path management
Ensures paths work regardless of execution context or working directory.
"""

import os
from pathlib import Path


# Determine project root dynamically
PROJECT_ROOT = Path(__file__).parent.parent

# Commonly used project paths
DATA_DIR = PROJECT_ROOT / 'data' / 'conversations'
OUTPUT_DIR = PROJECT_ROOT / 'output'
LOGS_DIR = PROJECT_ROOT / 'logs'
AUDIT_LOGS_DIR = LOGS_DIR / 'audit'
DEBUG_LOGS_DIR = LOGS_DIR / 'debug'
SCHEMA_DIR = PROJECT_ROOT / 'schema'
UTILS_DIR = PROJECT_ROOT / 'utils'
AGENTS_DIR = PROJECT_ROOT / 'agents'
SECURITY_DIR = PROJECT_ROOT / 'security'
VALIDATION_DIR = PROJECT_ROOT / 'validation'


def resolve_path(relative_path: str) -> Path:
    """
    Resolve a project-relative path to absolute path.
    
    Args:
        relative_path: Path relative to project root (e.g., 'data/conversations', './logs')
        
    Returns:
        Absolute Path object
        
    Example:
        >>> resolve_path('data/conversations/client_1')
        Path('D:/Atharva/Conversation/turtle-crm-agent/data/conversations/client_1')
    """
    # Handle both '.' and empty prefix
    rel_path = relative_path.lstrip('.').lstrip('/\\')
    return PROJECT_ROOT / rel_path if rel_path else PROJECT_ROOT


def ensure_path_exists(path: str | Path, is_dir: bool = False) -> Path:
    """
    Ensure path exists, creating if necessary.
    
    Args:
        path: Path to check/create (absolute or relative to project root)
        is_dir: If True, create as directory. If False, create parent directories only
        
    Returns:
        Absolute Path object
        
    Example:
        >>> ensure_path_exists('output', is_dir=True)
        Path('D:/Atharva/Conversation/turtle-crm-agent/output')
    """
    # Resolve to absolute path
    if isinstance(path, str):
        # If it's a relative path not starting with project, make it relative to project
        if not Path(path).is_absolute():
            p = PROJECT_ROOT / path
        else:
            p = Path(path)
    else:
        p = path
    
    if is_dir:
        p.mkdir(parents=True, exist_ok=True)
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
    
    return p.resolve()


def get_data_path(client_id: str = None, filename: str = None) -> Path:
    """
    Get path to conversation data directory or specific file.
    
    Args:
        client_id: e.g., 'client_1', 'client_2', 'lead_1', 'lead_2' (optional)
        filename: Specific file to load (optional)
        
    Returns:
        Path to directory or file
        
    Example:
        >>> get_data_path()
        Path('D:/Atharva/Conversation/turtle-crm-agent/data/conversations')
        >>> get_data_path('client_1')
        Path('D:/Atharva/Conversation/turtle-crm-agent/data/conversations/client_1')
        >>> get_data_path('client_1', 'Financial Planning.md')
        Path('D:/Atharva/Conversation/turtle-crm-agent/data/conversations/client_1/Financial Planning.md')
    """
    path = DATA_DIR
    if client_id:
        path = path / client_id
    if filename:
        path = path / filename
    return path


def get_output_path(filename: str = None) -> Path:
    """
    Get path to output directory or specific output file.
    
    Args:
        filename: Specific output file (optional)
        
    Returns:
        Path to directory or file
        
    Example:
        >>> get_output_path()
        Path('D:/Atharva/Conversation/turtle-crm-agent/output')
        >>> get_output_path('extraction_client_1.json')
        Path('D:/Atharva/Conversation/turtle-crm-agent/output/extraction_client_1.json')
    """
    path = ensure_path_exists(OUTPUT_DIR, is_dir=True)
    if filename:
        path = path / filename
    return path


def get_log_path(log_type: str = 'audit', filename: str = None) -> Path:
    """
    Get path to log directory or specific log file.
    
    Args:
        log_type: 'audit', 'debug', or custom type
        filename: Specific log file (optional)
        
    Returns:
        Path to directory or file
        
    Example:
        >>> get_log_path('audit')
        Path('D:/Atharva/Conversation/turtle-crm-agent/logs/audit')
        >>> get_log_path('debug', 'orchestrator.log')
        Path('D:/Atharva/Conversation/turtle-crm-agent/logs/debug/orchestrator.log')
    """
    log_dir = LOGS_DIR / log_type
    ensure_path_exists(log_dir, is_dir=True)
    
    if filename:
        return log_dir / filename
    return log_dir


def get_schema_path(filename: str = None) -> Path:
    """
    Get path to schema directory or specific schema file.
    
    Args:
        filename: Specific schema file (optional)
        
    Returns:
        Path to directory or file
        
    Example:
        >>> get_schema_path()
        Path('D:/Atharva/Conversation/turtle-crm-agent/schema')
        >>> get_schema_path('crm_schema.json')
        Path('D:/Atharva/Conversation/turtle-crm-agent/schema/crm_schema.json')
    """
    if filename:
        return SCHEMA_DIR / filename
    return SCHEMA_DIR


def get_env_path(env_var: str, default_relative_path: str) -> Path:
    """
    Get path from environment variable with fallback to project-relative default.
    
    Args:
        env_var: Environment variable name
        default_relative_path: Default path relative to project root
        
    Returns:
        Absolute Path object
        
    Example:
        >>> get_env_path('DATA_DIR', 'data/conversations')
        Path('D:/Atharva/Conversation/turtle-crm-agent/data/conversations')
    """
    env_value = os.environ.get(env_var)
    if env_value:
        return Path(env_value).resolve()
    return resolve_path(default_relative_path)


if __name__ == "__main__":
    print("=" * 70)
    print("PROJECT PATH CONFIGURATION")
    print("=" * 70)
    print(f"Project Root:      {PROJECT_ROOT}")
    print(f"\nData Directory:    {DATA_DIR}")
    print(f"Output Directory:  {OUTPUT_DIR}")
    print(f"Logs Directory:    {LOGS_DIR}")
    print(f"Schema Directory:  {SCHEMA_DIR}")
    print(f"\nUtility Functions:")
    print(f"  • resolve_path(relative_path)")
    print(f"  • ensure_path_exists(path, is_dir)")
    print(f"  • get_data_path(client_id, filename)")
    print(f"  • get_output_path(filename)")
    print(f"  • get_log_path(log_type, filename)")
    print(f"  • get_schema_path(filename)")
    print(f"  • get_env_path(env_var, default_path)")
    print("=" * 70)
