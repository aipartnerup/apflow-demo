"""
Authentication routes for demo server

Provides endpoints for authentication-related functionality.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)


class AuthRoutes:
    """Routes for authentication"""

    async def handle_auto_login(self, request: Request) -> JSONResponse:
        """
        Handle auto-login request
        
        GET /auth/auto-login
        
        This endpoint triggers the SessionCookieMiddleware to generate and set the JWT token cookie.
        When called by webapp on startup:
        1. Request goes through SessionCookieMiddleware
        2. Middleware checks for demo_jwt_token cookie
        3. If not present, generates user_id from browser fingerprint and creates JWT token
        4. Sets demo_jwt_token cookie in response (httponly, 1 year expiration)
        5. Returns confirmation that auto-login is enabled
        
        After this call, all subsequent API requests will automatically include the cookie,
        and aipartnerupflow's JWT middleware will extract the token from the cookie.
        
        Returns:
            JSONResponse with auto_login_enabled flag
        """
        return JSONResponse(
            content={
                "auto_login_enabled": True,
                "message": "Auto-login is enabled via browser cookies",
                "auth_method": "cookie",
            }
        )

