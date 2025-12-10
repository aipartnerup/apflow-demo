"""
User identification utilities for demo environment

Implements browser fingerprinting + session cookie hybrid approach
for stable user identification without requiring user registration.
"""

import hashlib
import uuid
from typing import Optional
from starlette.requests import Request


def generate_user_id_from_request(request: Request) -> str:
    """
    Generate stable user ID for demo environment
    
    Priority:
    1. Session cookie (demo_session_id) - most stable
    2. Browser fingerprint (User-Agent + IP + headers) - reasonably stable
    3. Fallback to "anonymous" - last resort
    
    Args:
        request: Starlette request object
        
    Returns:
        User ID string (format: "demo_user_{id}")
    """
    # Priority 1: Check session cookie
    session_id = request.cookies.get("demo_session_id")
    if session_id:
        return f"demo_user_{session_id}"
    
    # Priority 2: Generate browser fingerprint
    fingerprint_components = [
        request.headers.get("User-Agent", ""),
        request.headers.get("Accept-Language", ""),
        request.headers.get("Accept-Encoding", ""),
        request.headers.get("Accept", ""),
        request.client.host if request.client else "",
    ]
    
    fingerprint_string = "|".join(fingerprint_components)
    if fingerprint_string.strip():
        fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
        return f"demo_user_{fingerprint_hash}"
    
    # Priority 3: Fallback to anonymous
    return "anonymous"


def get_or_create_session_id(request: Request) -> str:
    """
    Get existing session ID from cookie or generate new one
    
    Args:
        request: Starlette request object
        
    Returns:
        Session ID string
    """
    session_id = request.cookies.get("demo_session_id")
    if not session_id:
        session_id = str(uuid.uuid4())[:16]  # Short UUID
    return session_id

