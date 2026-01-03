"""
Quota tracking hooks

Task tree lifecycle hooks to track task tree completion and update concurrency counters.

Uses apflow v0.6.0's register_task_tree_hook instead of post-hook with manual root task detection.
"""

from apflow.core.storage.sqlalchemy.models import TaskModel
from apflow_demo.extensions.rate_limiter import RateLimiter
from apflow_demo.config.settings import settings
from apflow.logger import get_logger

logger = get_logger(__name__)


async def quota_tracking_on_tree_completed(root_task: TaskModel, status: str) -> None:
    """
    Task tree lifecycle hook to track task tree completion
    
    This hook is called when a task tree completes (explicit lifecycle event).
    No need to manually check if task is root - hook is only called for root tasks.
    
    Args:
        root_task: Root task of the completed task tree
        status: Task tree completion status (e.g., "completed", "failed")
    """
    if not settings.rate_limit_enabled:
        return
    
    try:
        # Only track completed task trees
        if status != "completed":
            return
        
        # Get user_id
        user_id = root_task.user_id or "anonymous"
        
        # Complete task tree tracking
        RateLimiter.complete_task_tree(
            user_id=user_id,
            task_tree_id=root_task.id,
        )
        
        logger.debug(f"Completed task tree tracking for {root_task.id} (user: {user_id})")
        
    except Exception as e:
        logger.warning(f"Error in quota tracking task tree hook: {str(e)}")
        # Don't fail task execution if hook fails

