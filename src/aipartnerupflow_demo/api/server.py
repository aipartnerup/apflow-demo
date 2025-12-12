"""
Demo API server

Wraps aipartnerupflow API with demo-specific middleware and quota-aware routes.

Uses aipartnerupflow v0.6.0's task_routes_class parameter for clean extension.
"""

import os
from typing import Any
from aipartnerupflow.api.a2a.server import create_a2a_server
from aipartnerupflow_demo.api.middleware.rate_limit import RateLimitMiddleware
from aipartnerupflow_demo.api.middleware.demo_mode import DemoModeMiddleware
from aipartnerupflow_demo.api.middleware.session_cookie import SessionCookieMiddleware
from aipartnerupflow_demo.api.routes.quota_task_routes import QuotaTaskRoutes
from aipartnerupflow_demo.utils.jwt_utils import verify_demo_jwt_token
from aipartnerupflow_demo.config.settings import settings
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)


def create_demo_app() -> Any:
    """
    Create demo application with middleware and quota-aware routes
    
    Uses aipartnerupflow/api/a2a/server.py's create_a2a_server() directly with:
    - auto_initialize_extensions=True: Automatically initializes extensions
    - task_routes_class=QuotaTaskRoutes: Uses quota-aware TaskRoutes
    - verify_token_func: Uses demo JWT verification for cookie-based tokens
    
    Returns:
        Starlette/FastAPI application instance
    """
    # Set environment variables for aipartnerupflow
    aipartnerupflow_env = settings.get_aipartnerupflow_env()
    for key, value in aipartnerupflow_env.items():
        os.environ[key] = value
    
    # Create base aipartnerupflow application using create_a2a_server() directly
    # This leverages aipartnerupflow's new API structure
    logger.info("Creating A2A server with quota-aware TaskRoutes and auto-initialized extensions")
    
    custom_app = create_a2a_server(
        verify_token_func=verify_demo_jwt_token,  # Demo JWT verification for cookie-based tokens
        verify_token_secret_key=settings.aipartnerupflow_jwt_secret_key,
        verify_token_algorithm=settings.aipartnerupflow_jwt_algorithm,
        base_url=settings.aipartnerupflow_base_url,
        enable_system_routes=settings.aipartnerupflow_enable_system_routes,
        enable_docs=settings.aipartnerupflow_enable_docs,
        task_routes_class=QuotaTaskRoutes,  # Quota-aware TaskRoutes
        auto_initialize_extensions=True,  # Automatically initialize extensions
    )
    
    # Build the app to get the actual Starlette application
    base_app = custom_app.build()
    
    # Add demo middleware
    # Note: Middleware order matters - add them in reverse order of execution
    # (last added is first executed)
    
    # Add session cookie middleware (runs first, sets demo_jwt_token cookie)
    # This enables browser fingerprinting + JWT token generation for user identification
    # Cookie: httponly=True, max_age=1 year, samesite=lax
    # JWT token is added to Authorization header for aipartnerupflow's JWT middleware
    base_app.add_middleware(SessionCookieMiddleware)
    
    # Add demo mode middleware (runs after session cookie)
    if settings.demo_mode:
        base_app.add_middleware(DemoModeMiddleware)
    
    # Add rate limiting middleware (runs after demo mode)
    if settings.rate_limit_enabled:
        base_app.add_middleware(RateLimitMiddleware)
    
    # Add authentication routes (always available for demo server)
    from starlette.routing import Route
    from starlette.requests import Request
    from aipartnerupflow_demo.api.routes.auth_routes import AuthRoutes
    
    auth_routes = AuthRoutes()
    
    async def auto_login_handler(request: Request):
        return await auth_routes.handle_auto_login(request)
    
    # Add auth routes
    base_app.routes.append(
        Route("/auth/auto-login", auto_login_handler, methods=["GET"])
    )
    logger.info("Added auth route: /auth/auto-login")
    
    # Add quota status routes if rate limiting is enabled
    if settings.rate_limit_enabled:
        from aipartnerupflow_demo.api.routes.quota_routes import QuotaRoutes
        
        quota_routes = QuotaRoutes()
        
        async def quota_status_handler(request: Request):
            return await quota_routes.handle_quota_status(request)
        
        async def quota_system_stats_handler(request: Request):
            return await quota_routes.handle_system_stats(request)
        
        # Add quota routes
        base_app.routes.append(
            Route("/api/quota/status", quota_status_handler, methods=["GET"])
        )
        base_app.routes.append(
            Route("/api/quota/system-stats", quota_system_stats_handler, methods=["GET"])
        )
        logger.info("Added quota status routes: /api/quota/status, /api/quota/system-stats")
    
    # Add demo routes (always available for demo server)
    from aipartnerupflow_demo.api.routes.demo_routes import DemoRoutes
    
    demo_routes = DemoRoutes()
    
    async def init_demo_tasks_handler(request: Request):
        return await demo_routes.handle_init_demo_tasks(request)
    
    async def init_executor_demo_tasks_handler(request: Request):
        return await demo_routes.handle_init_executor_demo_tasks(request)
    
    # Add demo routes
    base_app.routes.append(
        Route("/api/demo/tasks/init", init_demo_tasks_handler, methods=["POST"])
    )
    base_app.routes.append(
        Route("/api/demo/tasks/init-executors", init_executor_demo_tasks_handler, methods=["POST"])
    )
    logger.info("Added demo routes: /api/demo/tasks/init, /api/demo/tasks/init-executors")
    
    # Add executor metadata routes (always available for demo server)
    from aipartnerupflow_demo.api.routes.executor_routes import ExecutorRoutes
    
    executor_routes = ExecutorRoutes()
    
    async def all_executor_metadata_handler(request: Request):
        return await executor_routes.handle_all_executor_metadata(request)
    
    async def executor_metadata_handler(request: Request):
        # Extract executor_id from URL path
        # Path format: /api/executors/metadata/{executor_id}
        path = request.url.path
        if path == "/api/executors/metadata":
            # Handle all executors metadata
            return await executor_routes.handle_all_executor_metadata(request)
        elif path.startswith("/api/executors/metadata/"):
            # Handle specific executor metadata
            executor_id = path.replace("/api/executors/metadata/", "", 1)
            if executor_id:
                return await executor_routes.handle_executor_metadata(request, executor_id)
        # If path doesn't match, return error
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"error": "Not found"}
        )
    
    # Add executor routes (single route handles both cases)
    base_app.routes.append(
        Route("/api/executors/metadata", executor_metadata_handler, methods=["GET"])
    )
    base_app.routes.append(
        Route("/api/executors/metadata/{executor_id}", executor_metadata_handler, methods=["GET"])
    )
    logger.info("Added executor metadata routes: /api/executors/metadata, /api/executors/metadata/{executor_id}")
    
    return base_app

