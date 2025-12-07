"""
Demo mode middleware

Note: This middleware is a placeholder. Actual demo result interception
should be implemented at the route level or through custom route handlers
that wrap aipartnerupflow routes, as body reading in middleware can be complex.

For now, this middleware just tracks demo mode status.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from aipartnerupflow_demo.config.settings import settings


class DemoModeMiddleware(BaseHTTPMiddleware):
    """
    Middleware for demo mode
    
    Note: Actual demo result interception should be done at route level.
    This middleware currently just adds demo mode header for downstream use.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Add demo mode information to request"""
        
        if settings.demo_mode:
            # Add demo mode header for downstream routes
            request.state.demo_mode = True
        
        response = await call_next(request)
        return response

