"""
Main entry point for aipartnerupflow-demo
"""

import os
import sys
import uvicorn
from pathlib import Path
from aipartnerupflow_demo.api.server import create_demo_app
from aipartnerupflow_demo.config.settings import settings


def main():
    """Main entry point"""
    # Load environment variables from .env file if it exists
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    # Initialize database tables for quota tracking if rate limiting is enabled
    if settings.rate_limit_enabled:
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
            print("Initialized quota tracking database tables")
        except Exception as e:
            print(f"Warning: Failed to initialize quota tracking tables: {e}")
    
    # Register quota tracking hooks if rate limiting is enabled
    if settings.rate_limit_enabled:
        try:
            # Register task tree lifecycle hook (v0.6.0 feature)
            from aipartnerupflow import register_task_tree_hook
            from aipartnerupflow_demo.extensions.quota_hooks import quota_tracking_on_tree_completed
            
            # Use decorator syntax
            registered_hook = register_task_tree_hook("on_tree_completed")(quota_tracking_on_tree_completed)
            print("Registered quota tracking task tree lifecycle hook")
        except Exception as e:
            print(f"Warning: Failed to register task tree lifecycle hook: {e}")
        
        try:
            # Register executor-specific hooks for LLM executors (v0.6.0 feature)
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
                    print(f"Registered quota check hook for {executor_id}")
                except Exception as e:
                    # Executor may not be registered yet, that's OK
                    print(f"Warning: Could not register hook for {executor_id}: {e}")
        except Exception as e:
            print(f"Warning: Failed to register executor hooks: {e}")
    
    # Create demo application
    app = create_demo_app()
    
    # Get host and port from settings
    host = settings.aipartnerupflow_api_host
    port = settings.aipartnerupflow_api_port
    
    print(f"Starting aipartnerupflow-demo on {host}:{port}")
    print(f"Demo mode: {settings.demo_mode}")
    print(f"Rate limiting: {settings.rate_limit_enabled}")
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=1,  # Single worker for async app
        loop="asyncio",
        limit_concurrency=100,
        limit_max_requests=1000,
        access_log=True,
    )


if __name__ == "__main__":
    main()

