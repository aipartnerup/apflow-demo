"""
Executor-specific hooks for quota checking

Uses apflow v0.6.0's executor-specific hooks instead of wrapper pattern.
"""

from typing import Any, Dict
from apflow.core.utils.logger import get_logger
from apflow_demo.extensions.rate_limiter import RateLimiter
from apflow_demo.utils.task_detection import is_llm_consuming_task_schema

logger = get_logger(__name__)


async def quota_check_pre_hook(executor: Any, task: Any, inputs: Dict[str, Any]) -> None:
    """
    Executor-specific pre_hook to check quota before LLM executor execution
    
    Uses apflow v0.6.0's built-in demo mode by setting use_demo=True
    instead of returning demo data directly.
    
    Note: LLM API keys are extracted from headers in QuotaLimitMiddleware and passed
    via params, so executors can access them. This hook only handles quota checking.
    
    Args:
        executor: Executor instance
        task: TaskModel instance
        inputs: Task inputs (can be modified to add use_demo)
        
    Returns:
        None (continues execution) or dict (skips execution - not used here)
    """
    from apflow_demo.config.settings import settings
    
    if not settings.rate_limit_enabled:
        return None
    
    try:
        # Check if LLM-consuming executor
        if not is_llm_consuming_task_schema(task.schemas):
            return None  # Non-LLM executor, continue execution
        
        # Get user_id from task
        user_id = task.user_id or "anonymous"
        
        # Check if user has LLM key
        # Priority: inputs (just set above) > task.metadata > task.params
        has_llm_key = bool(
            inputs.get("llm_api_key") or inputs.get("api_key") or
            (hasattr(task, 'metadata') and task.metadata and task.metadata.get("has_llm_key", False)) or
            (hasattr(task, 'params') and task.params and (task.params.get("llm_api_key") or task.params.get("api_key")))
        )
        
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
            
            # Use apflow v0.6.0's built-in demo mode
            inputs["use_demo"] = True
            
            return None  # Continue with demo mode
        
        return None  # Continue normally
        
    except Exception as e:
        logger.warning(f"Error in quota check pre-hook: {str(e)}")
        # Don't fail execution if hook fails
        return None

