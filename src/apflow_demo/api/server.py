"""
Demo API server

Wraps apflow API with demo-specific middleware and quota-aware routes.

Uses apflow's create_runnable_app() directly with all configuration.
"""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List
from starlette.routing import Route
from starlette.requests import Request
from apflow.api.main import create_runnable_app
from apflow_demo.api.middleware.rate_limit import RateLimitMiddleware
from apflow_demo.api.middleware.demo_mode import DemoModeMiddleware
from apflow_demo.api.middleware.session_cookie import SessionCookieMiddleware
from apflow_demo.api.middleware.quota_limit import QuotaLimitMiddleware
from apflow_demo.utils.jwt_utils import verify_demo_jwt_token
from apflow_demo.config.settings import settings
from apflow.logger import get_logger

logger = get_logger(__name__)


def _create_custom_routes() -> List[Route]:
    """
    Create custom routes for demo application
    
    Returns:
        List of Route objects
    """
    routes = []
    
    # Authentication routes
    from apflow_demo.api.routes.auth_routes import AuthRoutes
    auth_routes = AuthRoutes()
    
    async def auto_login_handler(request: Request):
        return await auth_routes.handle_auto_login(request)
    
    routes.append(Route("/auth/auto-login", auto_login_handler, methods=["GET"]))
    logger.info("Added auth route: /auth/auto-login")
    
    # Quota status routes (if rate limiting is enabled)
    if settings.rate_limit_enabled:
        from apflow_demo.api.routes.quota_routes import QuotaRoutes
        quota_routes = QuotaRoutes()
        
        async def quota_status_handler(request: Request):
            return await quota_routes.handle_quota_status(request)
        
        async def quota_system_stats_handler(request: Request):
            return await quota_routes.handle_system_stats(request)
        
        routes.append(Route("/api/quota/status", quota_status_handler, methods=["GET"]))
        routes.append(Route("/api/quota/system-stats", quota_system_stats_handler, methods=["GET"]))
        logger.info("Added quota status routes: /api/quota/status, /api/quota/system-stats")
    
    # Demo routes
    from apflow_demo.api.routes.demo_routes import DemoRoutes
    demo_routes = DemoRoutes()
    
    async def init_executor_demo_tasks_handler(request: Request):
        return await demo_routes.handle_init_executor_demo_tasks(request)
    
    async def check_demo_init_status_handler(request: Request):
        return await demo_routes.handle_check_demo_init_status(request)
    
    routes.append(Route("/api/demo/tasks/init-executors", init_executor_demo_tasks_handler, methods=["POST"]))
    routes.append(Route("/api/demo/tasks/init-status", check_demo_init_status_handler, methods=["GET"]))
    logger.info("Added demo routes: /api/demo/tasks/init-executors (POST), /api/demo/tasks/init-status (GET)")
    
    # Executor metadata routes
    from apflow_demo.api.routes.executor_routes import ExecutorRoutes
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
    
    # Session cookie middleware (runs first, sets authorization cookie)
    # This enables browser fingerprinting + JWT token generation for user identification
    # Cookie: httponly=True, max_age=1 year, samesite=lax
    # JWT token is added to Authorization header for apflow's JWT middleware
    middleware.append(SessionCookieMiddleware)
    
    # Demo mode middleware (runs after session cookie)
    if settings.demo_mode:
        middleware.append(DemoModeMiddleware)
    
    # Quota limit middleware (runs after demo mode, checks task tree quotas)
    if settings.rate_limit_enabled:
        middleware.append(QuotaLimitMiddleware)
    
    # Rate limiting middleware (runs after quota limit, general rate limiting)
    if settings.rate_limit_enabled:
        middleware.append(RateLimitMiddleware)
    
    return middleware


@asynccontextmanager
async def _app_lifespan(app: Any) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager for startup and shutdown
    
    Handles cleanup of database connections and other resources on shutdown.
    """
    # Startup
    logger.info("Application startup")
    yield
    
    # Shutdown - cleanup database connections
    logger.info("Application shutdown - cleaning up resources")
    try:
        # Try to get engine and close connections
        # First try get_default_engine if it exists
        try:
            from apflow.core.storage import get_default_engine
            engine = get_default_engine()
            if engine is not None:
                # Close all connections in the pool
                if hasattr(engine, "dispose"):
                    if hasattr(engine.dispose, "__call__"):
                        # Check if it's async
                        import inspect
                        if inspect.iscoroutinefunction(engine.dispose):
                            await engine.dispose()
                        else:
                            engine.dispose()
                    else:
                        engine.dispose()
                logger.info("Database connection pool closed")
        except (ImportError, AttributeError):
            # If get_default_engine doesn't exist, try to get engine from session
            try:
                from apflow.core.storage import get_default_session
                session = get_default_session()
                if session is not None and hasattr(session, "bind"):
                    engine = session.bind
                    if engine is not None and hasattr(engine, "dispose"):
                        if hasattr(engine.dispose, "__call__"):
                            import inspect
                            if inspect.iscoroutinefunction(engine.dispose):
                                await engine.dispose()
                            else:
                                engine.dispose()
                        logger.info("Database connection pool closed via session")
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Error during shutdown cleanup: {e}")
    
    logger.info("Shutdown complete")


def create_demo_app() -> Any:
    """
    Create demo application with middleware and quota-aware routes
    
    Uses apflow's create_runnable_app() directly with all configuration.
    This function handles:
    - Loading .env file from project directory
    - Initializing extensions (executors, hooks, storage backends)
    - Loading custom TaskModel if specified
    - Auto-initializing examples if database is empty
    - Creating the application with custom verify_token_func, routes, and middleware
    - Adding lifespan context manager for proper resource cleanup
    
    Returns:
        Starlette/FastAPI application instance
    """
    # Set environment variables for apflow
    # Note: Although apflow can read from os.environ directly, we need to:
    # 1. Convert types (int -> str, bool -> "true"/"false")
    # 2. Ensure default values are set (from settings object)
    # 3. Guarantee variables are set before create_runnable_app() is called
    apflow_env = settings.get_apflow_env()
    for key, value in apflow_env.items():
        os.environ[key] = value
    
    logger.info("Creating demo application with apflow's create_runnable_app()")
    
    # Use create_runnable_app() directly - it handles everything:
    # - Loads .env file from project directory
    # - Initializes extensions (executors, hooks, storage backends)
    # - Loads custom TaskModel if specified
    # - Auto-initializes examples if database is empty
    # - Creates the application with all configuration
    app = create_runnable_app(
        protocol="a2a",
        verify_token_func=verify_demo_jwt_token,  # Demo JWT verification for cookie-based tokens
        # No custom task_routes_class - quota logic is handled by QuotaLimitMiddleware
        custom_routes=_create_custom_routes(),  # Custom routes
        custom_middleware=_create_custom_middleware(),  # Custom middleware
        auto_initialize_extensions=True,  # Automatically initialize extensions
    )
    
    # Add lifespan context manager for proper resource cleanup on shutdown
    # This ensures database connections are properly closed when the app shuts down
    try:
        from fastapi import FastAPI
        from starlette.applications import Starlette
        
        if isinstance(app, FastAPI):
            # FastAPI app - use lifespan parameter
            # Note: We can't modify lifespan after creation, so we log a warning
            # The lifespan should ideally be passed to create_runnable_app if it supports it
            logger.debug("FastAPI app detected - lifespan should be set during app creation")
        elif isinstance(app, Starlette):
            # Starlette app - try to set lifespan_context on router
            # lifespan_context should be a callable that takes app and returns async context manager
            if hasattr(app, "router"):
                original_lifespan = getattr(app.router, "lifespan_context", None)
                if original_lifespan is None:
                    # Assign the function itself, not the result of calling it
                    app.router.lifespan_context = _app_lifespan
                    logger.debug("Added lifespan context manager to Starlette app")
                else:
                    # Wrap existing lifespan
                    @asynccontextmanager
                    async def _wrapped_lifespan(app: Any) -> AsyncGenerator[None, None]:
                        async with original_lifespan(app):
                            async with _app_lifespan(app):
                                yield
                    app.router.lifespan_context = _wrapped_lifespan
                    logger.debug("Wrapped existing lifespan context manager")
    except Exception as e:
        logger.warning(f"Could not add lifespan context manager: {e}")
    
    return app
