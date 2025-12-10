"""
Session cookie middleware

Sets demo_session_id cookie on first request for user identification.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from aipartnerupflow_demo.utils.user_identification import get_or_create_session_id
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)


class SessionCookieMiddleware(BaseHTTPMiddleware):
    """Set demo_session_id cookie on first request"""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and set session cookie if needed"""
        # Get or create session ID
        session_id = get_or_create_session_id(request)
        
        # Process request
        response = await call_next(request)
        
        # Set cookie if not already set
        if "demo_session_id" not in request.cookies:
            response.set_cookie(
                key="demo_session_id",
                value=session_id,
                max_age=30 * 24 * 60 * 60,  # 30 days
                httponly=True,
                samesite="lax",
                secure=False,  # Set to True in production with HTTPS
            )
            logger.debug(f"Set demo_session_id cookie: {session_id}")
        
        return response

