"""
Quota status routes

Provides endpoints for checking quota status and usage statistics.
"""

from typing import Optional
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException, status

from aipartnerupflow_demo.extensions.rate_limiter import RateLimiter
from aipartnerupflow_demo.utils.header_utils import (
    has_llm_key_in_header,
    extract_user_id_from_request,
)
from aipartnerupflow_demo.config.settings import settings
from aipartnerupflow.core.utils.logger import get_logger
from datetime import datetime, timezone

logger = get_logger(__name__)


class QuotaRoutes:
    """Routes for quota status and management"""
    
    async def handle_quota_status(self, request: Request) -> JSONResponse:
        """
        Handle quota status request
        
        GET /api/quota/status
        """
        try:
            # Extract user_id: JWT > Cookie > Browser fingerprinting
            # extract_user_id_from_request now handles all fallbacks automatically
            user_id = extract_user_id_from_request(request)
            is_premium = has_llm_key_in_header(request)
            
            quota_status = await RateLimiter.get_user_quota_status(
                user_id=user_id,
                has_llm_key=is_premium,
            )
            
            # Add reset time
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            return JSONResponse(
                content={
                    "user_id": user_id,
                    "quota": {
                        **quota_status,
                        "reset_time": tomorrow.isoformat(),
                    },
                    "is_premium": is_premium,
                }
            )
        except Exception as e:
            logger.error(f"Error getting quota status: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    async def handle_system_stats(self, request: Request) -> JSONResponse:
        """
        Handle system statistics request (admin only)
        
        GET /api/quota/system-stats
        """
        try:
            # Note: Admin authentication check is a future enhancement.
            # Currently, the system stats endpoint is open to all users for demo purposes.
            # In production, consider adding authentication/authorization checks here.
            
            # Get global concurrency from database
            # Get global concurrency from database
            from aipartnerupflow.core.storage import create_pooled_session
            from aipartnerupflow_demo.storage.quota_repository import QuotaRepository
            
            try:
                async with create_pooled_session() as session:
                    repo = QuotaRepository(session)
                    total_concurrent = repo.get_concurrency_count("system", "global")
            except Exception as e:
                logger.warning(f"Failed to get concurrency from database: {e}")
                total_concurrent = 0
            
            return JSONResponse(
                content={
                    "total_concurrent": total_concurrent,
                    "max_concurrent": settings.max_concurrent_task_trees,
                    "quota_config": {
                        "free_user_total_limit": settings.rate_limit_daily_per_user,
                        "free_user_llm_limit": settings.rate_limit_daily_llm_per_user,
                        "premium_user_total_limit": settings.rate_limit_daily_per_user_premium,
                        "max_concurrent_per_user": settings.max_concurrent_task_trees_per_user,
                    },
                }
            )
        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

