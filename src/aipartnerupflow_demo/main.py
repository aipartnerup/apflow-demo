"""
Main entry point for aipartnerupflow-demo

This is the demo application layer that extends aipartnerupflow with
quota management, rate limiting, and demo task initialization features.

Follows the structure pattern from aipartnerupflow/api/main.py for consistency.
"""

import os
import sys
import warnings
import uvicorn
import time
from pathlib import Path
from typing import Any
from aipartnerupflow_demo.api.server import create_demo_app
from aipartnerupflow_demo.config.settings import settings
from aipartnerupflow.core.utils.logger import get_logger

# Suppress specific warnings for cleaner output
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="uvicorn")

# Add project root to Python path for development
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Initialize logger
logger = get_logger(__name__)
start_time = time.time()
logger.info("Starting aipartnerupflow-demo service")


def _load_environment_variables():
    """Load environment variables from .env file if it exists"""
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.debug(f"Loaded environment variables from {env_file}")


def _initialize_database_tables():
    """Initialize database tables for quota tracking if rate limiting is enabled"""
    
    # Register custom TaskModel BEFORE initializing tables
    # This ensures the custom model is used when tables are created/accessed
    try:
        from aipartnerupflow.core.config import set_task_model_class
        from aipartnerupflow_demo.storage.models import CustomTaskModel
        set_task_model_class(CustomTaskModel)
        logger.info("Registered custom TaskModel with token_usage and instance_id fields")
    except Exception as e:
        logger.warning(f"Failed to register custom TaskModel: {e}")
    
    if not settings.rate_limit_enabled:
        return
    
    try:
        from aipartnerupflow.core.storage import get_default_session
        from aipartnerupflow_demo.storage.models import (
            QuotaCounter,
            ConcurrencyCounter,
            TaskTreeTracking,
            UsageStats,
        )
        from aipartnerupflow.core.storage.sqlalchemy.models import Base
        
        # Create tables if they don't exist
        session = get_default_session()
        Base.metadata.create_all(bind=session.bind, checkfirst=True)
        logger.info("Initialized quota tracking database tables")
    except Exception as e:
        logger.warning(f"Failed to initialize quota tracking tables: {e}")


def _register_quota_hooks():
    """Register quota tracking hooks if rate limiting is enabled"""
    if not settings.rate_limit_enabled:
        return
    
    # Register task tree lifecycle hook
    try:
        from aipartnerupflow import register_task_tree_hook
        from aipartnerupflow_demo.extensions.quota_hooks import quota_tracking_on_tree_completed
        
        registered_hook = register_task_tree_hook("on_tree_completed")(quota_tracking_on_tree_completed)
        logger.info("Registered quota tracking task tree lifecycle hook")
    except Exception as e:
        logger.warning(f"Failed to register task tree lifecycle hook: {e}")
    
    # Register executor-specific hooks for LLM executors
    try:
        from aipartnerupflow.core.extensions.registry import add_executor_hook
        from aipartnerupflow_demo.extensions.quota_executor_hooks import quota_check_pre_hook
        
        # Register for LLM-consuming executors
        llm_executors = [
            "crewai_executor",
            "generate_executor",
            "openai_executor",
            "anthropic_executor",
            "llm_executor",
        ]
        
        for executor_id in llm_executors:
            try:
                add_executor_hook(executor_id, "pre_hook", quota_check_pre_hook)
                logger.debug(f"Registered quota check hook for {executor_id}")
            except Exception as e:
                # Executor may not be registered yet, that's OK
                logger.debug(f"Could not register hook for {executor_id}: {e}")
    except Exception as e:
        logger.warning(f"Failed to register executor hooks: {e}")


def main():
    """
    Main entry point for demo API service
    
    Uses aipartnerupflow's create_runnable_app() with:
    - auto_initialize_extensions=True: Automatically initializes extensions
    - QuotaLimitMiddleware: Handles quota checking and task tree tracking
    
    Then registers demo-specific hooks and middleware.
    """
    # Load environment variables
    _load_environment_variables()
    
    # Initialize database tables for quota tracking (before creating app)
    _initialize_database_tables()
    
    # Create demo application
    # create_demo_app() will use create_runnable_app() with auto_initialize_extensions=True
    # This automatically initializes extensions and loads custom TaskModel
    # QuotaLimitMiddleware handles quota checking and task tree tracking
    app = create_demo_app()
    
    # Register quota tracking hooks after app creation
    # Hooks must be registered after extensions are initialized (which happens in create_demo_app)
    _register_quota_hooks()
    
    # Log startup time
    startup_time = time.time() - start_time
    logger.info(f"Service initialization completed in {startup_time:.2f} seconds")
    
    # Get host and port from settings
    host = settings.aipartnerupflow_api_host
    port = settings.aipartnerupflow_api_port
    
    logger.info(f"Starting aipartnerupflow-demo on {host}:{port}")
    logger.info(f"Demo mode: {settings.demo_mode}")
    logger.info(f"Rate limiting: {settings.rate_limit_enabled}")
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=1,  # Single worker for async app
        loop="asyncio",  # Use asyncio event loop
        limit_concurrency=100,  # Increase concurrency limit
        limit_max_requests=1000,  # Increase max requests
        access_log=True,  # Enable access logging for debugging
    )


if __name__ == "__main__":
    main()

