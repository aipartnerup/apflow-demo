"""
Demo routes for demo task initialization

Provides endpoints for initializing demo tasks for users.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse
from apflow_demo.services.demo_init import DemoInitService
from apflow_demo.utils.header_utils import extract_user_id_from_request
from apflow.logger import get_logger

logger = get_logger(__name__)


class DemoRoutes:
    """Routes for demo task initialization"""

    def __init__(self):
        """Initialize demo routes with service"""
        self.demo_init_service = DemoInitService()

    async def handle_check_demo_init_status(self, request: Request) -> JSONResponse:
        """
        Handle demo init status check request
        
        GET /api/demo/tasks/init-status
        
        This endpoint:
        1. Extracts user_id from JWT token (via middleware) or request
        2. Checks which executors already have demo tasks for this user
        3. Returns status information including:
           - Whether demo init can be performed
           - List of executors with/without demo tasks
           - Details for each executor
        
        Returns:
            JSONResponse with status information
        """
        try:
            # Extract user_id from request (JWT/cookie/browser fingerprint)
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
            
            # Check demo init status
            status = await self.demo_init_service.check_demo_init_status(user_id)
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "can_init": status["can_init"],
                    "total_executors": status["total_executors"],
                    "existing_executors": status["existing_executors"],
                    "missing_executors": status["missing_executors"],
                    "executor_details": status["executor_details"],
                    "message": (
                        f"Demo init can be performed. {len(status['missing_executors'])} executors need demo tasks."
                        if status["can_init"]
                        else f"All {status['total_executors']} executors already have demo tasks."
                    ),
                }
            )
            
        except Exception as e:
            logger.error(f"Error checking demo init status: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "status_check_failed",
                    "message": f"Failed to check demo init status: {str(e)}",
                }
            )

    async def handle_init_executor_demo_tasks(self, request: Request) -> JSONResponse:
        """
        Handle executor demo task initialization request
        
        POST /api/demo/tasks/init-executors
        
        This endpoint:
        1. Extracts user_id from JWT token (via middleware) or request
        2. Creates demo tasks for all executors based on executor_metadata
        3. Returns success response with created task count and IDs
        
        Each executor gets one demo task with:
        - executor_id as schemas.method
        - Demo inputs generated from executor's input_schema
        - Task name based on executor name
        
        User identification is automatic via JWT/cookie middleware.
        The created tasks will appear in the normal task list via apflow's standard API.
        
        Returns:
            JSONResponse with success status, created_count, task_ids, and message
        """
        try:
            # Extract user_id from request (JWT/cookie/browser fingerprint)
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
            
            logger.info(f"Initializing executor demo tasks for user: {user_id[:20]}...")
            
            # Initialize executor demo tasks for this user
            created_task_ids = await self.demo_init_service.init_executor_demo_tasks_for_user(user_id)
            
            if not created_task_ids:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "created_count": 0,
                        "task_ids": [],
                        "message": "No executor demo tasks were created (no executors found)",
                    }
                )
            
            logger.info(f"Successfully initialized {len(created_task_ids)} executor demo tasks for user: {user_id[:20]}...")
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "created_count": len(created_task_ids),
                    "task_ids": created_task_ids,
                    "message": f"Executor demo tasks initialized successfully. Created {len(created_task_ids)} tasks.",
                }
            )
            
        except Exception as e:
            logger.error(f"Error initializing executor demo tasks: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "initialization_failed",
                    "message": f"Failed to initialize executor demo tasks: {str(e)}",
                }
            )

