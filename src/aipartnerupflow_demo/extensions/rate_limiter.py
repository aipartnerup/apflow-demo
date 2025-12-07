"""
Rate limiter extension for demo deployment

Implements per-user and per-IP daily rate limiting using Redis.
"""

import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional
import redis
from aipartnerupflow_demo.config.settings import settings


class RateLimiter:
    """Rate limiter for demo deployment"""
    
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
                # Test connection
                cls._redis_client.ping()
            except Exception as e:
                print(f"Warning: Redis connection failed: {e}. Rate limiting disabled.")
                return None
        return cls._redis_client
    
    @classmethod
    def _get_user_key(cls, user_id: Optional[str]) -> Optional[str]:
        """Get rate limit key for user"""
        if not user_id:
            return None
        return f"rate_limit:user:{user_id}"
    
    @classmethod
    def _get_ip_key(cls, ip_address: str) -> str:
        """Get rate limit key for IP"""
        return f"rate_limit:ip:{ip_address}"
    
    @classmethod
    def _get_today_key(cls, base_key: str) -> str:
        """Get key for today's date"""
        today = datetime.now(timezone.utc).date().isoformat()
        return f"{base_key}:{today}"
    
    @classmethod
    def check_limit(
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
            info_dict contains: allowed, user_count, user_limit, ip_count, ip_limit
        """
        if not settings.rate_limit_enabled:
            return True, {"allowed": True, "reason": "rate_limiting_disabled"}
        
        redis_client = cls._get_redis_client()
        if not redis_client:
            # If Redis is not available, allow request but log warning
            return True, {"allowed": True, "reason": "redis_unavailable"}
        
        limit_per_user = limit_per_user or settings.rate_limit_daily_per_user
        limit_per_ip = limit_per_ip or settings.rate_limit_daily_per_ip
        
        result = {
            "allowed": True,
            "user_count": 0,
            "user_limit": limit_per_user,
            "ip_count": 0,
            "ip_limit": limit_per_ip,
        }
        
        # Check user limit
        if user_id:
            user_key = cls._get_today_key(cls._get_user_key(user_id))
            user_count = redis_client.get(user_key)
            user_count = int(user_count) if user_count else 0
            
            result["user_count"] = user_count
            
            if user_count >= limit_per_user:
                result["allowed"] = False
                result["reason"] = "user_limit_exceeded"
                return False, result
        
        # Check IP limit
        if ip_address:
            ip_key = cls._get_today_key(cls._get_ip_key(ip_address))
            ip_count = redis_client.get(ip_key)
            ip_count = int(ip_count) if ip_count else 0
            
            result["ip_count"] = ip_count
            
            if ip_count >= limit_per_ip:
                result["allowed"] = False
                result["reason"] = "ip_limit_exceeded"
                return False, result
        
        return True, result
    
    @classmethod
    def increment(
        cls,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Increment rate limit counters
        
        Args:
            user_id: Optional user ID
            ip_address: IP address
        """
        if not settings.rate_limit_enabled:
            return
        
        redis_client = cls._get_redis_client()
        if not redis_client:
            return
        
        # Increment user counter
        if user_id:
            user_key = cls._get_today_key(cls._get_user_key(user_id))
            redis_client.incr(user_key)
            redis_client.expire(user_key, 86400)  # 24 hours
        
        # Increment IP counter
        if ip_address:
            ip_key = cls._get_today_key(cls._get_ip_key(ip_address))
            redis_client.incr(ip_key)
            redis_client.expire(ip_key, 86400)  # 24 hours
    
    @classmethod
    def get_usage(
        cls,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> dict:
        """
        Get current usage statistics
        
        Args:
            user_id: Optional user ID
            ip_address: IP address
            
        Returns:
            Dictionary with usage statistics
        """
        redis_client = cls._get_redis_client()
        if not redis_client:
            return {"user_count": 0, "ip_count": 0}
        
        result = {}
        
        if user_id:
            user_key = cls._get_today_key(cls._get_user_key(user_id))
            user_count = redis_client.get(user_key)
            result["user_count"] = int(user_count) if user_count else 0
            result["user_limit"] = settings.rate_limit_daily_per_user
        
        if ip_address:
            ip_key = cls._get_today_key(cls._get_ip_key(ip_address))
            ip_count = redis_client.get(ip_key)
            result["ip_count"] = int(ip_count) if ip_count else 0
            result["ip_limit"] = settings.rate_limit_daily_per_ip
        
        return result

