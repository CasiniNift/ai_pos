import os
from typing import Optional
import warnings

def load_environment():
    """Load environment variables from .env file if it exists"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

def get_claude_key() -> Optional[str]:
    """Get Claude API key from environment variables"""
    load_environment()
    
    possible_keys = [
        "ANTHROPIC_API_KEY",
        "CLAUDE_API_KEY", 
        "CLAUDE_KEY",
        "ANTHROPIC_KEY"
    ]
    
    for key_name in possible_keys:
        api_key = os.getenv(key_name)
        if api_key:
            return api_key
    
    return None

def validate_claude_key(api_key: str) -> bool:
    """Basic validation of Claude API key format"""
    if not api_key:
        return False
    
    if api_key.startswith('sk-ant-') and len(api_key) > 50:
        return True
    
    return False

# Backward compatibility
def get_openai_key() -> Optional[str]:
    """Deprecated: Use get_claude_key() instead"""
    return get_claude_key()

def validate_api_key(api_key: str) -> bool:
    """Deprecated: Use validate_claude_key() instead"""
    return validate_claude_key(api_key)

def get_model_name() -> str:
    """Get the Claude model to use, with fallback"""
    load_environment()
    return os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")

def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    load_environment()
    debug = os.getenv("DEBUG", "False").lower()
    return debug in ("true", "1", "yes", "on")

def get_port() -> int:
    """Get the port to run the application on"""
    load_environment()
    try:
        return int(os.getenv("PORT", "7860"))
    except ValueError:
        return 7860

def setup_warnings():
    """Setup appropriate warnings for production/development"""
    if not is_debug_mode():
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)

