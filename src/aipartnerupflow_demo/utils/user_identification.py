"""
User identification utilities for demo environment

Implements browser fingerprinting + persistent cookie hybrid approach
for stable user identification without requiring user registration.

Cookie: demo_user_id (httponly, max_age=1 year)
"""

import hashlib
import uuid
from typing import Optional
from starlette.requests import Request
from starlette.datastructures import Headers


def generate_user_id_from_fingerprint(headers: Headers) -> str:
    """
    Generate stable user ID from browser fingerprint
    
    Uses a combination of browser headers to create a consistent fingerprint
    that persists across sessions for the same browser/device.
    
    Args:
        headers: Request headers
        
    Returns:
        User ID string (format: "demo_user_{hash}")
    """
    # Collect fingerprint components (order matters for consistency)
    fingerprint_components = [
        headers.get("User-Agent", ""),
        headers.get("Accept-Language", ""),
        headers.get("Accept-Encoding", ""),
        headers.get("Accept", ""),
        headers.get("Sec-CH-UA", ""),  # Client Hints
        headers.get("Sec-CH-UA-Mobile", ""),
        headers.get("Sec-CH-UA-Platform", ""),
    ]
    
    # Create fingerprint string
    fingerprint_string = "|".join(fingerprint_components)
    
    if not fingerprint_string.strip():
        # Fallback: generate random ID
        return f"demo_user_{uuid.uuid4().hex[:16]}"
    
    # Generate consistent hash (use first 16 chars for readability)
    fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
    return f"demo_user_{fingerprint_hash}"


def get_or_create_user_id(request: Request) -> str:
    """
    Get existing user ID from cookie or generate new one from fingerprint
    
    This function is used by middleware to ensure every request has a user_id.
    
    Args:
        request: Starlette request object
        
    Returns:
        User ID string
    """
    # Check if cookie already exists
    user_id = request.cookies.get("demo_user_id")
    if user_id:
        return user_id
    
    # Generate from fingerprint (will be set as cookie in middleware)
    return generate_user_id_from_fingerprint(request.headers)


def generate_user_id_from_request(request: Request) -> str:
    """
    Generate stable user ID for demo environment (legacy function, kept for compatibility)
    
    Priority:
    1. Session cookie (demo_user_id) - most stable
    2. Browser fingerprint - reasonably stable
    
    Args:
        request: Starlette request object
        
    Returns:
        User ID string
    """
    # Check cookie first
    user_id = request.cookies.get("demo_user_id")
    if user_id:
        return user_id
    
    # Generate from fingerprint
    return generate_user_id_from_fingerprint(request.headers)

