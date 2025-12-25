"""
Database-based rate limiter extension

Uses the same database as aipartnerupflow (DuckDB/PostgreSQL) instead of Redis.
"""

from datetime import datetime, timezone
from typing import Optional
from aipartnerupflow.core.storage import create_pooled_session
from aipartnerupflow_demo.storage.quota_repository import QuotaRepository
from aipartnerupflow_demo.config.settings import settings


class RateLimiter:
    """Rate limiter using database storage (same as aipartnerupflow)"""
    
    # _get_repository is removed as we use create_pooled_session directly
    
    @classmethod
    async def check_limit(
        cls,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit_per_user: Optional[int] = None,
        limit_per_ip: Optional[int] = None,
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit
        
        Args:
            user_id: Optional user ID
            ip_address: IP address
            limit_per_user: Override per-user limit
            limit_per_ip: Override per-IP limit
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        if not settings.rate_limit_enabled:
            return True, {"allowed": True, "reason": "rate_limiting_disabled"}
        
        if not settings.rate_limit_enabled:
            return True, {"allowed": True, "reason": "rate_limiting_disabled"}
        
        try:
            async with create_pooled_session() as session:
                repo = QuotaRepository(session)
                
                limit_per_user = limit_per_user or settings.rate_limit_daily_per_user
                limit_per_ip = limit_per_ip or settings.rate_limit_daily_per_ip
                
                today = datetime.now(timezone.utc).date().isoformat()
                
                result = {
                    "allowed": True,
                    "user_count": 0,
                    "user_limit": limit_per_user,
                    "ip_count": 0,
                    "ip_limit": limit_per_ip,
                }
                
                # Check user limit
                if user_id:
                    user_count = await repo.get_quota_count(user_id, today, "total")
                    result["user_count"] = user_count
                    
                    if user_count >= limit_per_user:
                        result["allowed"] = False
                        result["reason"] = "user_limit_exceeded"
                        return False, result
                
                # Check IP limit (using IP as user_id for tracking)
                if ip_address:
                    ip_count = await repo.get_quota_count(f"ip:{ip_address}", today, "total")
                    result["ip_count"] = ip_count
                    
                    if ip_count >= limit_per_ip:
                        result["allowed"] = False
                        result["reason"] = "ip_limit_exceeded"
                        return False, result
                
                return True, result
        except Exception as e:
            print(f"Warning: Failed to check limit: {e}")
            return True, {"allowed": True, "reason": "database_error"}
    
    @classmethod
    async def record_request(
        cls,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Record a request (increment counters)
        
        Args:
            user_id: Optional user ID
            ip_address: IP address
        """
        if not settings.rate_limit_enabled:
            return
        
        if not settings.rate_limit_enabled:
            return
        
        try:
            async with create_pooled_session() as session:
                repo = QuotaRepository(session)
                
                today = datetime.now(timezone.utc).date().isoformat()
                
                if user_id:
                    await repo.increment_quota_count(user_id, today, "total", 1)
                
                if ip_address:
                    await repo.increment_quota_count(f"ip:{ip_address}", today, "total", 1)
        except Exception as e:
            print(f"Warning: Failed to record request: {e}")
    
    @classmethod
    async def check_task_tree_quota(
        cls,
        user_id: str,
        is_llm_consuming: bool,
        has_llm_key: bool = False,
    ) -> tuple[bool, dict]:
        """
        Check if user can create a new task tree
        
        Args:
            user_id: User ID
            is_llm_consuming: Whether the task tree is LLM-consuming
            has_llm_key: Whether user has LLM key in header (premium user)
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        if not settings.rate_limit_enabled:
            return True, {"allowed": True, "reason": "rate_limiting_disabled"}
        
        if not settings.rate_limit_enabled:
            return True, {"allowed": True, "reason": "rate_limiting_disabled"}
        
        try:
            async with create_pooled_session() as session:
                repo = QuotaRepository(session)
                
                today = datetime.now(timezone.utc).date().isoformat()
                
                # Get current counts
                total_count = await repo.get_quota_count(user_id, today, "total")
                llm_count = await repo.get_quota_count(user_id, today, "llm")
                
                # Determine limits based on user type
                if has_llm_key:
                    # Premium user: 10 total, no separate LLM limit
                    total_limit = settings.rate_limit_daily_per_user_premium
                    llm_limit = total_limit  # No separate limit for premium users
                else:
                    # Free user: 10 total, only 1 LLM-consuming
                    total_limit = settings.rate_limit_daily_per_user
                    llm_limit = settings.rate_limit_daily_llm_per_user
                
                result = {
                    "allowed": True,
                    "total_count": total_count,
                    "total_limit": total_limit,
                    "llm_count": llm_count,
                    "llm_limit": llm_limit,
                    "is_premium": has_llm_key,
                }
                
                # Check total quota
                if total_count >= total_limit:
                    result["allowed"] = False
                    result["reason"] = "total_quota_exceeded"
                    return False, result
                
                # Check LLM-consuming quota (only for free users)
                if not has_llm_key and is_llm_consuming:
                    if llm_count >= llm_limit:
                        result["allowed"] = False
                        result["reason"] = "llm_quota_exceeded"
                        result["llm_quota_exceeded"] = True
                        return False, result
                
                return True, result
        except Exception as e:
            print(f"Warning: Failed to check task tree quota: {e}")
            return True, {"allowed": True, "reason": "database_error"}
    
    @classmethod
    async def check_concurrency_limit(
        cls,
        user_id: str,
    ) -> tuple[bool, dict]:
        """
        Check if user can start a new concurrent task tree
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        if not settings.rate_limit_enabled:
            return True, {"allowed": True, "reason": "rate_limiting_disabled"}
        
        if not settings.rate_limit_enabled:
            return True, {"allowed": True, "reason": "rate_limiting_disabled"}
        
        try:
            async with create_pooled_session() as session:
                repo = QuotaRepository(session)
                
                # Check global concurrency
                global_current = await repo.get_concurrency_count("system", "global")
                global_limit = settings.max_concurrent_task_trees
                
                # Check user concurrency
                user_current = await repo.get_concurrency_count("user", user_id)
                user_limit = settings.max_concurrent_task_trees_per_user
                
                result = {
                    "allowed": True,
                    "global_current": global_current,
                    "global_limit": global_limit,
                    "user_current": user_current,
                    "user_limit": user_limit,
                }
                
                # Check global limit
                if global_current >= global_limit:
                    result["allowed"] = False
                    result["reason"] = "system_concurrency_limit_exceeded"
                    return False, result
                
                # Check user limit
                if user_current >= user_limit:
                    result["allowed"] = False
                    result["reason"] = "user_concurrency_limit_exceeded"
                    return False, result
                
                return True, result
        except Exception as e:
            print(f"Warning: Failed to check concurrency limit: {e}")
            return True, {"allowed": True, "reason": "database_error"}
    
    @classmethod
    async def start_task_tree(
        cls,
        user_id: str,
        task_tree_id: str,
        is_llm_consuming: bool,
    ) -> bool:
        """
        Start tracking a task tree
        
        Args:
            user_id: User ID
            task_tree_id: Task tree ID
            is_llm_consuming: Whether task tree is LLM-consuming
            
        Returns:
            True if tracking started successfully
        """
        if not settings.rate_limit_enabled:
            return False
        
        if not settings.rate_limit_enabled:
            return False
        
        try:
            async with create_pooled_session() as session:
                repo = QuotaRepository(session)
                
                today = datetime.now(timezone.utc).date().isoformat()
                
                # Increment quota counters
                await repo.increment_quota_count(user_id, today, "total", 1)
                if is_llm_consuming:
                    await repo.increment_quota_count(user_id, today, "llm", 1)
                
                # Increment concurrency counters
                await repo.increment_concurrency("system", "global", 1)
                await repo.increment_concurrency("user", user_id, 1)
                
                # Start task tree tracking
                await repo.start_task_tree(task_tree_id, user_id, is_llm_consuming)
                
                return True
        except Exception as e:
            print(f"Warning: Failed to start task tree tracking: {e}")
            return False
    
    @classmethod
    async def complete_task_tree(
        cls,
        user_id: str,
        task_tree_id: str,
    ) -> None:
        """
        Complete tracking for a task tree
        
        Args:
            user_id: User ID
            task_tree_id: Task tree ID
        """
        if not settings.rate_limit_enabled:
            return
        
        if not settings.rate_limit_enabled:
            return
        
        try:
            async with create_pooled_session() as session:
                repo = QuotaRepository(session)
                
                # Get task tree tracking to check if it was LLM-consuming
                tracking = await repo.complete_task_tree(task_tree_id)
                
                if tracking:
                    # Decrement concurrency counters
                    await repo.decrement_concurrency("system", "global", 1)
                    await repo.decrement_concurrency("user", user_id, 1)
        except Exception as e:
            print(f"Warning: Failed to complete task tree tracking: {e}")
    
    @classmethod
    async def get_user_quota_status(
        cls,
        user_id: str,
        has_llm_key: bool = False,
    ) -> dict:
        """
        Get user's quota status
        
        Args:
            user_id: User ID
            has_llm_key: Whether user has LLM key (premium user)
            
        Returns:
            Dictionary with quota status information
        """
        if not settings.rate_limit_enabled:
            return {
                "rate_limiting_enabled": False,
                "total_used": 0,
                "total_limit": 0,
                "llm_used": 0,
                "llm_limit": 0,
            }
        
        if not settings.rate_limit_enabled:
            return {
                "rate_limiting_enabled": False,
                "total_used": 0,
                "total_limit": 0,
                "llm_used": 0,
                "llm_limit": 0,
            }
        
        try:
            async with create_pooled_session() as session:
                repo = QuotaRepository(session)
                
                today = datetime.now(timezone.utc).date().isoformat()
                
                total_used = await repo.get_quota_count(user_id, today, "total")
                llm_used = await repo.get_quota_count(user_id, today, "llm")
                
                if has_llm_key:
                    total_limit = settings.rate_limit_daily_per_user_premium
                    llm_limit = total_limit
                else:
                    total_limit = settings.rate_limit_daily_per_user
                    llm_limit = settings.rate_limit_daily_llm_per_user
                
                # Check if quotas are exceeded
                total_quota_exceeded = total_used >= total_limit
                llm_quota_exceeded = not has_llm_key and llm_used >= llm_limit
                
                return {
                    "rate_limiting_enabled": True,
                    "total_used": total_used,
                    "total_limit": total_limit,
                    "total_remaining": max(0, total_limit - total_used),
                    "total_quota_exceeded": total_quota_exceeded,
                    "llm_used": llm_used,
                    "llm_limit": llm_limit,
                    "llm_remaining": max(0, llm_limit - llm_used),
                    "llm_quota_exceeded": llm_quota_exceeded,
                    "is_premium": has_llm_key,
                }
        except Exception as e:
            print(f"Warning: Failed to get user quota status: {e}")
            return {
                "rate_limiting_enabled": True,
                "database_unavailable": True,
                "total_used": 0,
                "total_limit": 0,
                "llm_used": 0,
                "llm_limit": 0,
            }

