"""
Demo routes for demo task initialization

Provides endpoints for initializing demo tasks for users.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse
from aipartnerupflow_demo.services.demo_init import DemoInitService
from aipartnerupflow_demo.utils.header_utils import extract_user_id_from_request
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)


class DemoRoutes:
    """Routes for demo task initialization"""

    def __init__(self):
        """Initialize demo routes with service"""
        self.demo_init_service = DemoInitService()

    async def handle_init_demo_tasks(self, request: Request) -> JSONResponse:
        """
        Handle demo task initialization request
        
        POST /api/demo/tasks/init
        
        This endpoint:
        1. Extracts user_id from JWT token (via middleware) or request
        2. Creates demo tasks for the current user
        3. Returns success response with created task count and IDs
        
        User identification is automatic via JWT/cookie middleware.
        The created tasks will appear in the normal task list via aipartnerupflow's standard API.
        
        Returns:
            JSONResponse with success status, created_count, task_ids, and message
        """
        try:
            # Extract user_id from request (JWT/cookie/browser fingerprint)
            # This uses the same mechanism as quota routes
            user_id = extract_user_id_from_request(request)
            
            if not user_id:
                logger.error("Failed to extract user_id from request")
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": "user_id_not_found",
                        "message": "Unable to identify user. Please ensure authentication is configured.",
                    }
                )
            
            logger.info(f"Initializing demo tasks for user: {user_id[:20]}...")
            
            # Initialize demo tasks for this user
            created_task_ids = await self.demo_init_service.init_demo_tasks_for_user(user_id)
            
            if not created_task_ids:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "created_count": 0,
                        "task_ids": [],
                        "message": "No demo tasks were created (may already exist)",
                    }
                )
            
            logger.info(f"Successfully initialized {len(created_task_ids)} demo tasks for user: {user_id[:20]}...")
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "created_count": len(created_task_ids),
                    "task_ids": created_task_ids,
                    "message": f"Demo tasks initialized successfully. Created {len(created_task_ids)} tasks.",
                }
            )
            
        except Exception as e:
            logger.error(f"Error initializing demo tasks: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "initialization_failed",
                    "message": f"Failed to initialize demo tasks: {str(e)}",
                }
            )

