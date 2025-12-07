"""
Usage tracker extension

Tracks demo usage statistics for analytics.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import redis
from aipartnerupflow_demo.config.settings import settings


class UsageTracker:
    """Track demo usage statistics"""
    
    _redis_client: Optional[redis.Redis] = None
    
    @classmethod
    def _get_redis_client(cls) -> Optional[redis.Redis]:
        """Get Redis client (singleton)"""
        if cls._redis_client is None:
            try:
                cls._redis_client = redis.from_url(
                    settings.redis_url,
                    db=settings.redis_db,
                    decode_responses=True
                )
                cls._redis_client.ping()
            except Exception:
                return None
        return cls._redis_client
    
    @classmethod
    async def track_request(
        cls,
        endpoint: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track a request
        
        Args:
            endpoint: API endpoint
            user_id: Optional user ID
            ip_address: IP address
            metadata: Optional metadata
        """
        redis_client = cls._get_redis_client()
        if not redis_client:
            return
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Store request log
        log_key = f"usage:requests:{datetime.now(timezone.utc).date().isoformat()}"
        log_entry = {
            "timestamp": timestamp,
            "endpoint": endpoint,
            "user_id": user_id,
            "ip_address": ip_address,
            "metadata": metadata or {},
        }
        redis_client.lpush(log_key, json.dumps(log_entry))
        redis_client.expire(log_key, 86400 * 7)  # Keep for 7 days
    
    @classmethod
    async def track_task_execution(
        cls,
        task_id: str,
        user_id: Optional[str] = None,
        used_demo_result: bool = False,
    ) -> None:
        """
        Track task execution
        
        Args:
            task_id: Task ID
            user_id: Optional user ID
            used_demo_result: Whether demo result was used
        """
        redis_client = cls._get_redis_client()
        if not redis_client:
            return
        
        # Increment counters
        today = datetime.now(timezone.utc).date().isoformat()
        
        # Total tasks
        redis_client.incr(f"usage:tasks:total:{today}")
        redis_client.expire(f"usage:tasks:total:{today}", 86400 * 7)
        
        # Demo tasks
        if used_demo_result:
            redis_client.incr(f"usage:tasks:demo:{today}")
            redis_client.expire(f"usage:tasks:demo:{today}", 86400 * 7)
        
        # Per user
        if user_id:
            redis_client.incr(f"usage:tasks:user:{user_id}:{today}")
            redis_client.expire(f"usage:tasks:user:{user_id}:{today}", 86400 * 7)
    
    @classmethod
    async def get_stats(cls, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics
        
        Args:
            date: Date in ISO format (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with statistics
        """
        redis_client = cls._get_redis_client()
        if not redis_client:
            return {}
        
        if date is None:
            date = datetime.now(timezone.utc).date().isoformat()
        
        total_tasks = redis_client.get(f"usage:tasks:total:{date}")
        demo_tasks = redis_client.get(f"usage:tasks:demo:{date}")
        
        return {
            "date": date,
            "total_tasks": int(total_tasks) if total_tasks else 0,
            "demo_tasks": int(demo_tasks) if demo_tasks else 0,
        }

