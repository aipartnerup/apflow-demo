"""
Demo API server

Wraps aipartnerupflow API with demo-specific middleware and quota-aware routes.

Uses aipartnerupflow's create_runnable_app() directly with all configuration.
"""

import os
from typing import Any, List
from starlette.routing import Route
from starlette.requests import Request
from aipartnerupflow.api.main import create_runnable_app
from aipartnerupflow_demo.api.middleware.rate_limit import RateLimitMiddleware
from aipartnerupflow_demo.api.middleware.demo_mode import DemoModeMiddleware
from aipartnerupflow_demo.api.middleware.session_cookie import SessionCookieMiddleware
from aipartnerupflow_demo.api.routes.quota_task_routes import QuotaTaskRoutes
from aipartnerupflow_demo.utils.jwt_utils import verify_demo_jwt_token
from aipartnerupflow_demo.config.settings import settings
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)


def _create_custom_routes() -> List[Route]:
    """
    Create custom routes for demo application
    
    Returns:
        List of Route objects
    """
    routes = []
    
    # Authentication routes
    from aipartnerupflow_demo.api.routes.auth_routes import AuthRoutes
    auth_routes = AuthRoutes()
    
    async def auto_login_handler(request: Request):
        return await auth_routes.handle_auto_login(request)
    
    routes.append(Route("/auth/auto-login", auto_login_handler, methods=["GET"]))
    logger.info("Added auth route: /auth/auto-login")
    
    # Quota status routes (if rate limiting is enabled)
    if settings.rate_limit_enabled:
        from aipartnerupflow_demo.api.routes.quota_routes import QuotaRoutes
        quota_routes = QuotaRoutes()
        
        async def quota_status_handler(request: Request):
            return await quota_routes.handle_quota_status(request)
        
        async def quota_system_stats_handler(request: Request):
            return await quota_routes.handle_system_stats(request)
        
        routes.append(Route("/api/quota/status", quota_status_handler, methods=["GET"]))
        routes.append(Route("/api/quota/system-stats", quota_system_stats_handler, methods=["GET"]))
        logger.info("Added quota status routes: /api/quota/status, /api/quota/system-stats")
    
    # Demo routes
    from aipartnerupflow_demo.api.routes.demo_routes import DemoRoutes
    demo_routes = DemoRoutes()
    
    async def init_executor_demo_tasks_handler(request: Request):
        return await demo_routes.handle_init_executor_demo_tasks(request)
    
    routes.append(Route("/api/demo/tasks/init-executors", init_executor_demo_tasks_handler, methods=["POST"]))
    logger.info("Added demo route: /api/demo/tasks/init-executors")
    
    # Executor metadata routes
    from aipartnerupflow_demo.api.routes.executor_routes import ExecutorRoutes
    executor_routes = ExecutorRoutes()
    
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
    
    routes.append(Route("/api/executors/metadata", executor_metadata_handler, methods=["GET"]))
    routes.append(Route("/api/executors/metadata/{executor_id}", executor_metadata_handler, methods=["GET"]))
    logger.info("Added executor metadata routes: /api/executors/metadata, /api/executors/metadata/{executor_id}")
    
    return routes


def _create_custom_middleware() -> List:
    """
    Create custom middleware for demo application
    
    Returns:
        List of middleware classes
    """
    middleware = []
    
    # Session cookie middleware (runs first, sets demo_jwt_token cookie)
    # This enables browser fingerprinting + JWT token generation for user identification
    # Cookie: httponly=True, max_age=1 year, samesite=lax
    # JWT token is added to Authorization header for aipartnerupflow's JWT middleware
    middleware.append(SessionCookieMiddleware)
    
    # Demo mode middleware (runs after session cookie)
    if settings.demo_mode:
        middleware.append(DemoModeMiddleware)
    
    # Rate limiting middleware (runs after demo mode)
    if settings.rate_limit_enabled:
        middleware.append(RateLimitMiddleware)
    
    return middleware


def create_demo_app() -> Any:
    """
    Create demo application with middleware and quota-aware routes
    
    Uses aipartnerupflow's create_runnable_app() directly with all configuration.
    This function handles:
    - Loading .env file from project directory
    - Initializing extensions (executors, hooks, storage backends)
    - Loading custom TaskModel if specified
    - Auto-initializing examples if database is empty
    - Creating the application with custom verify_token_func, routes, and middleware
    
    Returns:
        Starlette/FastAPI application instance
    """
    # Set environment variables for aipartnerupflow
    aipartnerupflow_env = settings.get_aipartnerupflow_env()
    for key, value in aipartnerupflow_env.items():
        os.environ[key] = value
    
    logger.info("Creating demo application with aipartnerupflow's create_runnable_app()")
    
    # Use create_runnable_app() directly - it handles everything:
    # - Loads .env file from project directory
    # - Initializes extensions (executors, hooks, storage backends)
    # - Loads custom TaskModel if specified
    # - Auto-initializes examples if database is empty
    # - Creates the application with all configuration
    app = create_runnable_app(
        protocol="a2a",
        verify_token_func=verify_demo_jwt_token,  # Demo JWT verification for cookie-based tokens
        task_routes_class=QuotaTaskRoutes,  # Quota-aware TaskRoutes
        custom_routes=_create_custom_routes(),  # Custom routes
        custom_middleware=_create_custom_middleware(),  # Custom middleware
        auto_initialize_extensions=True,  # Automatically initialize extensions
    )
    
    return app
