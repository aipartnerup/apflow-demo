"""
Database-based usage tracker extension

Uses the same database as apflow (DuckDB/PostgreSQL) instead of Redis.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from apflow.core.storage import get_default_session
from apflow_demo.storage.quota_repository import QuotaRepository
from apflow_demo.config.settings import settings


class UsageTracker:
    """Usage tracker using database storage (same as apflow)"""
    
    @classmethod
    def _get_repository(cls) -> Optional[QuotaRepository]:
        """Get quota repository instance"""
        if not settings.rate_limit_enabled:
            return None
        
        try:
            session = get_default_session()
            return QuotaRepository(session)
        except Exception as e:
            print(f"Warning: Failed to get database session: {e}. Usage tracking disabled.")
            return None
    
    @classmethod
    def log_task_execution(
        cls,
        task_id: str,
        user_id: Optional[str] = None,
        is_demo: bool = False,
        inputs: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None,
    ) -> None:
        """
        Log task execution
        
        Args:
            task_id: Task ID
            user_id: Optional user ID
            is_demo: Whether this was a demo execution
            inputs: Optional task inputs
            result: Optional task result
        """
        if not settings.rate_limit_enabled:
            return
        
        repo = cls._get_repository()
        if not repo:
            return
        
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            
            # Increment total task count
            repo.increment_usage_stat(today, "total", "global", 1)
            
            # Increment demo task count if demo
            if is_demo:
                repo.increment_usage_stat(today, "demo", "global", 1)
            
            # Increment user-specific count
            if user_id:
                repo.increment_usage_stat(today, "user", user_id, 1)
        except Exception as e:
            print(f"Warning: Failed to log task execution: {e}")
    
    @classmethod
    def get_usage_stats(
        cls,
        date: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get usage statistics
        
        Args:
            date: Date in ISO format (YYYY-MM-DD), defaults to today
            user_id: Optional user ID for user-specific stats
            
        Returns:
            Dictionary with usage statistics
        """
        if not settings.rate_limit_enabled:
            return {
                "date": date or datetime.now(timezone.utc).date().isoformat(),
                "total_tasks": 0,
                "demo_tasks": 0,
                "user_tasks": 0,
            }
        
        repo = cls._get_repository()
        if not repo:
            return {
                "date": date or datetime.now(timezone.utc).date().isoformat(),
                "database_unavailable": True,
                "total_tasks": 0,
                "demo_tasks": 0,
                "user_tasks": 0,
            }
        
        target_date = date or datetime.now(timezone.utc).date().isoformat()
        
        total_tasks = repo.get_usage_stat(target_date, "total", "global")
        demo_tasks = repo.get_usage_stat(target_date, "demo", "global")
        
        result = {
            "date": target_date,
            "total_tasks": total_tasks,
            "demo_tasks": demo_tasks,
        }
        
        if user_id:
            user_tasks = repo.get_usage_stat(target_date, "user", user_id)
            result["user_tasks"] = user_tasks
        
        return result

