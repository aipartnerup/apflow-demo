"""
Header parsing utilities for LLM key detection
"""

from typing import Optional
from starlette.requests import Request


def has_llm_key_in_header(request: Request) -> bool:
    """
    Check if request contains LLM API key in headers
    
    Args:
        request: Starlette request object
        
    Returns:
        True if LLM key is present in headers
    """
    # Check X-LLM-API-KEY header
    if request.headers.get("X-LLM-API-KEY"):
        return True
    
    # Check provider-specific headers
    if request.headers.get("X-OpenAI-API-KEY") or request.headers.get("X-Anthropic-API-KEY"):
        return True
    
    # Check Authorization header for LLM key pattern
    # Format: "Bearer <key>" or "provider:key"
    auth_header = request.headers.get("Authorization", "")
    if auth_header:
        # Check for Bearer token format
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            # Assume it's an LLM key if it's a reasonable length (API keys are usually long)
            if len(token) > 20:
                return True
        
        # Check for provider:key format
        if ":" in auth_header and len(auth_header.split(":")) == 2:
            parts = auth_header.split(":")
            provider = parts[0].strip().lower()
            key = parts[1].strip()
            if provider in ["openai", "anthropic", "google", "llm"] and len(key) > 20:
                return True
    
    return False


def extract_llm_key_from_header(request: Request) -> Optional[str]:
    """
    Extract LLM API key from headers
    
    Args:
        request: Starlette request object
        
    Returns:
        LLM API key if found, None otherwise
    """
    # Check X-LLM-API-KEY header
    llm_key = request.headers.get("X-LLM-API-KEY")
    if llm_key:
        return llm_key
    
    # Check provider-specific headers
    openai_key = request.headers.get("X-OpenAI-API-KEY")
    if openai_key:
        return openai_key
    
    anthropic_key = request.headers.get("X-Anthropic-API-KEY")
    if anthropic_key:
        return anthropic_key
    
    # Check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header:
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        
        if ":" in auth_header:
            parts = auth_header.split(":")
            if len(parts) == 2:
                return parts[1].strip()
    
    return None


def extract_user_id_from_request(request: Request) -> Optional[str]:
    """
    Extract user ID from request (from JWT or header)
    
    Args:
        request: Starlette request object
        
    Returns:
        User ID if found, None otherwise
    """
    # Try to get from request state (set by JWT middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return user_id
    
    # Try to get from header
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return user_id
    
    return None

