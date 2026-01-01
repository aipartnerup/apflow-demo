"""
Header parsing utilities

Uses apflow's built-in LLM key detection.
"""

from typing import Optional
from starlette.requests import Request


def has_llm_key_in_header(request: Request) -> bool:
    """
    Check if request contains LLM API key in headers
    
    Uses apflow's LLMAPIKeyMiddleware which extracts X-LLM-API-KEY header
    and stores it in thread-local context.
    
    Args:
        request: Starlette request object
        
    Returns:
        True if LLM key is present in headers
    """
    # Use apflow's built-in LLM key detection
    # LLMAPIKeyMiddleware extracts X-LLM-API-KEY header and stores it in context
    try:
        from apflow.core.utils.llm_key_context import get_llm_key_from_header
        
        # Check if LLM key is available in context (set by LLMAPIKeyMiddleware)
        llm_key = get_llm_key_from_header()
        if llm_key:
            return True
        
        # Fallback: Check header directly (in case middleware hasn't run yet)
        # This handles the case where we're checking before middleware processes the request
        if request.headers.get("X-LLM-API-KEY") or request.headers.get("x-llm-api-key"):
            return True
        
        return False
    except ImportError:
        # Fallback if apflow is not available (shouldn't happen)
        return bool(request.headers.get("X-LLM-API-KEY") or request.headers.get("x-llm-api-key"))


def extract_llm_key_from_header(request: Request) -> Optional[str]:
    """
    Extract LLM API key from headers
    
    Uses apflow's built-in LLM key extraction.
    
    Args:
        request: Starlette request object
        
    Returns:
        LLM API key if found, None otherwise
    """
    try:
        from apflow.core.utils.llm_key_context import get_llm_key_from_header
        
        # Get from context (set by LLMAPIKeyMiddleware)
        llm_key = get_llm_key_from_header()
        if llm_key:
            return llm_key
        
        # Fallback: Check header directly
        return request.headers.get("X-LLM-API-KEY") or request.headers.get("x-llm-api-key")
    except ImportError:
        # Fallback if apflow is not available
        return request.headers.get("X-LLM-API-KEY") or request.headers.get("x-llm-api-key")


def extract_user_id_from_request(request: Request) -> Optional[str]:
    """
    Extract user ID from request (from JWT, cookie, or browser fingerprint)
    
    Priority:
    1. JWT token (set by apflow JWT middleware) - for authenticated users
       This is the preferred method as it integrates with apflow's user_id extraction
    2. JWT token from cookie (authorization) - extract user_id from token
    3. Browser fingerprint - fallback for first-time visitors
    
    Args:
        request: Starlette request object
        
    Returns:
        User ID if found, None otherwise
    """
    # Priority 1: Try to get from request state (set by apflow JWT middleware)
    # This is set when JWT token is verified by JWTAuthenticationMiddleware
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return user_id
    
    # Priority 2: Try to extract from JWT token in cookie
    # This handles the case where cookie exists but JWT middleware hasn't processed it yet
    jwt_token = request.cookies.get("authorization")
    if jwt_token:
        from apflow_demo.utils.jwt_utils import get_user_id_from_token
        user_id = get_user_id_from_token(jwt_token)
        if user_id:
            return user_id
    
    # Priority 3: Generate from browser fingerprint (will be set as JWT cookie in middleware)
    # This ensures we always have a user_id, even for first-time visitors
    from apflow_demo.utils.user_identification import generate_user_id_from_fingerprint
    fingerprint_id = generate_user_id_from_fingerprint(request.headers)
    return fingerprint_id

