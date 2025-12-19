"""
Executor-specific hooks for quota checking

Uses aipartnerupflow v0.6.0's executor-specific hooks instead of wrapper pattern.
"""

from typing import Any, Dict
from aipartnerupflow.core.utils.logger import get_logger
from aipartnerupflow_demo.extensions.rate_limiter import RateLimiter
from aipartnerupflow_demo.utils.task_detection import is_llm_consuming_task_schema

logger = get_logger(__name__)


async def quota_check_pre_hook(executor: Any, task: Any, inputs: Dict[str, Any]) -> None:
    """
    Executor-specific pre_hook to check quota before LLM executor execution
    
    Uses aipartnerupflow v0.6.0's built-in demo mode by setting use_demo=True
    instead of returning demo data directly.
    
    Args:
        executor: Executor instance
        task: TaskModel instance
        inputs: Task inputs (can be modified to add use_demo)
        
    Returns:
        None (continues execution) or dict (skips execution - not used here)
    """
    from aipartnerupflow_demo.config.settings import settings
    
    if not settings.rate_limit_enabled:
        return None
    
    try:
        # Check if LLM-consuming executor
        if not is_llm_consuming_task_schema(task.schemas):
            return None  # Non-LLM executor, continue execution
        
        # Get user_id from task
        user_id = task.user_id or "anonymous"
        
        # Check if user has LLM key
        # Priority: task.metadata (set by QuotaLimitMiddleware) > task.params > inputs
        has_llm_key = False
        if hasattr(task, 'metadata') and task.metadata:
            has_llm_key = task.metadata.get("has_llm_key", False)
        elif hasattr(task, 'params') and task.params:
            # Check if LLM key is in params
            has_llm_key = bool(task.params.get("llm_api_key") or task.params.get("api_key"))
        elif inputs:
            # Check inputs for LLM key (fallback)
            has_llm_key = bool(inputs.get("llm_api_key") or inputs.get("api_key"))
        
        # Check quota status
        quota_status = RateLimiter.get_user_quota_status(
            user_id=user_id,
            has_llm_key=has_llm_key,
        )
        
        # If LLM quota exceeded and no LLM key, use built-in demo mode
        if quota_status.get('llm_quota_exceeded') and not has_llm_key:
            logger.info(
                f"LLM quota exceeded for task {task.id} (user: {user_id}), "
                f"using built-in demo mode"
            )
            
            # Use aipartnerupflow v0.6.0's built-in demo mode
            inputs["use_demo"] = True
            
            return None  # Continue with demo mode
        
        return None  # Continue normally
        
    except Exception as e:
        logger.warning(f"Error in quota check pre-hook: {str(e)}")
        # Don't fail execution if hook fails
        return None

