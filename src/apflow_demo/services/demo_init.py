"""
Demo task initialization service

Creates demo tasks for specific users, similar to init_examples_data but user-specific.
Also supports initializing demo tasks for all executors based on executor_metadata.
"""

from typing import List, Any, Optional, Dict
from datetime import datetime, timezone, timedelta
from apflow.core.storage import get_default_session
from apflow.core.storage.sqlalchemy.task_repository import TaskRepository
from apflow.core.config import get_task_model_class
from apflow.logger import get_logger

logger = get_logger(__name__)


class DemoInitService:
    """Service for initializing demo tasks for users"""

    async def init_demo_tasks_for_user(self, user_id: str) -> List[str]:
        """
        Initialize demo tasks for a specific user
        
        Note: The apflow.examples module has been removed from the core library.
        This method now returns an empty list. Use init_executor_demo_tasks_for_user()
        to initialize demo tasks based on executor metadata instead.
        
        Args:
            user_id: User ID to create tasks for
            
        Returns:
            List of created task IDs (empty list, as examples module is deprecated)
        """
        logger.warning(
            f"init_demo_tasks_for_user() is deprecated for user {user_id[:20] if user_id else 'unknown'}... "
            "The apflow.examples module has been removed. "
            "Use init_executor_demo_tasks_for_user() instead to initialize demo tasks "
            "based on executor metadata."
        )
        return []
    
    async def check_demo_init_status(self, user_id: str) -> Dict[str, Any]:
        """
        Check demo init status for a specific user
        
        Returns information about which executors already have demo tasks
        and which ones can be initialized.
        
        Args:
            user_id: User ID to check status for
            
        Returns:
            Dictionary with demo init status information
        """
        from apflow_demo.services.executor_demo_init import ExecutorDemoInitService
        
        executor_demo_service = ExecutorDemoInitService()
        return await executor_demo_service.check_demo_init_status(user_id)
    
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
        from apflow_demo.services.executor_demo_init import ExecutorDemoInitService
        
        executor_demo_service = ExecutorDemoInitService()
        return await executor_demo_service.init_all_executor_demo_tasks_for_user(user_id)

