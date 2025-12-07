"""
Demo API server

Wraps aipartnerupflow API with demo-specific middleware.
"""

import os
from typing import Any
from aipartnerupflow.api.main import create_app_by_protocol
from aipartnerupflow_demo.api.middleware.rate_limit import RateLimitMiddleware
from aipartnerupflow_demo.api.middleware.demo_mode import DemoModeMiddleware
from aipartnerupflow_demo.config.settings import settings


def create_demo_app() -> Any:
    """
    Create demo application with middleware
    
    Returns:
        Starlette/FastAPI application instance
    """
    # Set environment variables for aipartnerupflow
    aipartnerupflow_env = settings.get_aipartnerupflow_env()
    for key, value in aipartnerupflow_env.items():
        os.environ[key] = value
    
    # Create base aipartnerupflow application
    protocol = settings.aipartnerupflow_api_protocol
    base_app = create_app_by_protocol(protocol=protocol)
    
    # Add demo middleware
    # Note: Middleware order matters - add them in reverse order of execution
    # (last added is first executed)
    
    # Add demo mode middleware (runs first, can intercept requests)
    if settings.demo_mode:
        base_app.add_middleware(DemoModeMiddleware)
    
    # Add rate limiting middleware (runs after demo mode)
    if settings.rate_limit_enabled:
        base_app.add_middleware(RateLimitMiddleware)
    
    return base_app

