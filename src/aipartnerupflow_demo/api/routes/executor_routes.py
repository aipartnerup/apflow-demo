"""
Executor metadata routes

Provides endpoints for querying executor metadata using aipartnerupflow's
executor_metadata utilities.
"""

from typing import Optional
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException, status
from aipartnerupflow.core.extensions.executor_metadata import (
    get_executor_metadata,
    get_all_executor_metadata,
)
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutorRoutes:
    """Routes for executor metadata queries"""

    async def handle_all_executor_metadata(self, request: Request) -> JSONResponse:
        """
        Handle request to get all executor metadata
        
        GET /api/executors/metadata
        
        Returns:
            JSONResponse with all executor metadata
        """
        try:
            all_metadata = get_all_executor_metadata()
            
            return JSONResponse(
                content={
                    "executors": all_metadata,
                    "count": len(all_metadata),
                }
            )
        except Exception as e:
            logger.error(f"Error getting all executor metadata: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    async def handle_executor_metadata(
        self, request: Request, executor_id: str
    ) -> JSONResponse:
        """
        Handle request to get specific executor metadata
        
        GET /api/executors/metadata/{executor_id}
        
        Args:
            executor_id: Executor ID to get metadata for
            
        Returns:
            JSONResponse with executor metadata
        """
        try:
            metadata = get_executor_metadata(executor_id)
            
            if not metadata:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Executor '{executor_id}' not found"
                )
            
            return JSONResponse(content=metadata)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error getting executor metadata for '{executor_id}': {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

