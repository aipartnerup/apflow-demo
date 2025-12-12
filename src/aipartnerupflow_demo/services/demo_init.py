"""
Demo task initialization service

Creates demo tasks for specific users, similar to init_examples_data but user-specific.
Also supports initializing demo tasks for all executors based on executor_metadata.
"""

from typing import List, Any, Optional
from datetime import datetime, timezone, timedelta
from aipartnerupflow.core.storage import get_default_session
from aipartnerupflow.core.storage.sqlalchemy.task_repository import TaskRepository
from aipartnerupflow.core.config import get_task_model_class
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)


class DemoInitService:
    """Service for initializing demo tasks for users"""

    async def init_demo_tasks_for_user(self, user_id: str) -> List[str]:
        """
        Initialize demo tasks for a specific user
        
        Note: The aipartnerupflow.examples module has been removed from the core library.
        This method now returns an empty list. Use init_executor_demo_tasks_for_user()
        to initialize demo tasks based on executor metadata instead.
        
        Args:
            user_id: User ID to create tasks for
            
        Returns:
            List of created task IDs (empty list, as examples module is deprecated)
        """
        logger.warning(
            f"init_demo_tasks_for_user() is deprecated for user {user_id[:20] if user_id else 'unknown'}... "
            "The aipartnerupflow.examples module has been removed. "
            "Use init_executor_demo_tasks_for_user() instead to initialize demo tasks "
            "based on executor metadata."
        )
        return []
    
    async def init_executor_demo_tasks_for_user(self, user_id: str) -> List[str]:
        """
        Initialize demo tasks for all executors for a specific user
        
        Creates demo tasks based on executor_metadata:
        - One task per executor
        - Uses executor_id as schemas.method
        - Generates demo inputs from executor's input_schema
        - Sets task name based on executor name
        
        Args:
            user_id: User ID to create tasks for
            
        Returns:
            List of created task IDs
        """
        from aipartnerupflow_demo.services.executor_demo_init import ExecutorDemoInitService
        
        executor_demo_service = ExecutorDemoInitService()
        return await executor_demo_service.init_all_executor_demo_tasks_for_user(user_id)

