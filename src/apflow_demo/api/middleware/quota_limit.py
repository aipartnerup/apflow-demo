"""
Quota limit middleware for task routes

Handles all quota-related logic:
- Checks user quotas before processing requests
- Tracks task trees after generation/execution
- Adds quota info to responses

Note: LLM API keys are handled by apflow's LLMAPIKeyMiddleware,
which uses thread-local context instead of environment variables for security.
"""

import json
from typing import Any, Optional
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import status

from apflow_demo.extensions.rate_limiter import RateLimiter
from apflow_demo.utils.header_utils import (
    has_llm_key_in_header,
    extract_user_id_from_request,
)
from apflow_demo.utils.task_detection import detect_task_tree_from_tasks_array
from apflow_demo.config.settings import settings
from apflow.logger import get_logger

logger = get_logger(__name__)


class QuotaLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for checking task tree quotas before processing requests"""

    async def dispatch(self, request: Request, call_next):
        """Check quota limits for task requests"""
        
        # Skip quota checking for certain paths
        skip_paths = ["/health", "/docs", "/openapi.json", "/redoc", "/auth", "/api/quota", "/api/demo", "/api/executors"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # Only process JSON-RPC requests (A2A protocol)
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return await call_next(request)
        
        # Read and parse request body
        try:
            body_bytes = await request.body()
            if not body_bytes:
                return await call_next(request)
            
            # Store body bytes in request.state so route handlers can access them
            request.state.body_bytes = body_bytes
            
            body = json.loads(body_bytes.decode())
            method = body.get("method")
            
            # Only process tasks.generate and tasks.execute
            if method not in ["tasks.generate", "tasks.execute"]:
                # Store parsed body in request.state for route handlers
                request.state.parsed_body = body
                # Make body readable again for parent route handlers
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
                return await call_next(request)
            
            params = body.get("params", {})
            request_id = body.get("id")
            
            # Extract user info
            user_id = extract_user_id_from_request(request)
            is_premium = has_llm_key_in_header(request)
            
            # Detect if LLM-consuming
            is_llm_consuming = False
            if method == "tasks.generate":
                # Task generation always uses LLM
                is_llm_consuming = True
            elif method == "tasks.execute":
                # Check from tasks array or task_id
                tasks = params.get("tasks")
                task_id = params.get("task_id") or params.get("id")
                
                # Skip quota check for re-execution of existing tasks
                if task_id and not tasks:
                    # Check if task already exists (re-execution)
                    is_existing = await self._is_existing_task_tree(task_id)
                    if is_existing:
                        # Re-execution - skip quota check, just pass through
                        request.state.parsed_body = body
                        async def receive():
                            return {"type": "http.request", "body": body_bytes}
                        request._receive = receive
                        return await call_next(request)
                
                if tasks and isinstance(tasks, list):
                    is_llm_consuming = detect_task_tree_from_tasks_array(tasks)
                elif task_id:
                    # For execute with task_id, we'll check later in route
                    # Assume LLM-consuming for now, route will verify
                    is_llm_consuming = True
            
            # Check quota (only for new task trees)
            allowed, quota_info = await RateLimiter.check_task_tree_quota(
                user_id=user_id,
                is_llm_consuming=is_llm_consuming,
                has_llm_key=is_premium,
            )
            
            # Check concurrency limit
            concurrency_allowed, concurrency_info = await RateLimiter.check_concurrency_limit(user_id)
            
            # Store quota check results in request.state
            request.state.quota_check = {
                "allowed": allowed and concurrency_allowed,
                "quota_info": quota_info,
                "concurrency_info": concurrency_info,
                "is_llm_consuming": is_llm_consuming,
                "user_id": user_id,
                "is_premium": is_premium,
                "use_demo": False,
            }
            
            # Handle quota exceeded cases
            if not allowed:
                if is_premium:
                    # Premium user exceeded quota - reject immediately
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32001,
                                "message": "Daily task tree quota exceeded",
                                "data": {
                                    "reason": quota_info.get("reason"),
                                    "total_used": quota_info.get("total_count"),
                                    "total_limit": quota_info.get("total_limit"),
                                    "reset_time": self._get_reset_time(),
                                },
                            },
                        },
                    )
                else:
                    # Free user - set use_demo=True
                    if is_llm_consuming and quota_info.get("llm_quota_exceeded"):
                        logger.info(f"Free user {user_id} exceeded LLM quota, setting use_demo=True")
                        params["use_demo"] = True
                        request.state.quota_check["use_demo"] = True
            
            # Handle concurrency limit exceeded
            if not concurrency_allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32002,
                            "message": "Concurrency limit reached",
                            "data": {
                                "reason": concurrency_info.get("reason"),
                                "current_concurrent": concurrency_info.get("user_current"),
                                "max_concurrent": concurrency_info.get("user_limit"),
                            },
                        },
                    },
                )
            
            # Store parsed body and params (with potential use_demo modification) in request.state
            body["params"] = params
            request.state.parsed_body = body
            
            # Set metadata for executor hooks
            if "metadata" not in params:
                params["metadata"] = {}
            params["metadata"]["user_id"] = user_id
            params["metadata"]["has_llm_key"] = is_premium
            
            # Make body readable again for route handlers by replacing _receive
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive
            
            # Continue to route handler
            # Note: LLM API keys are handled by apflow's LLMAPIKeyMiddleware
            # which uses thread-local context, not environment variables
            response = await call_next(request)
            
            # Process response: track task trees and add quota info
            response = await self._process_response(
                response, method, params, request_id, user_id, is_llm_consuming, quota_info
            )
            
            return response
            
        except json.JSONDecodeError:
            # Invalid JSON - let route handler deal with it
            logger.warning("Invalid JSON in request body, passing to route handler")
            return await call_next(request)
        except Exception as e:
            # Error in quota checking - log but allow request to proceed
            logger.error(f"Error in quota limit middleware: {str(e)}", exc_info=True)
            return await call_next(request)
    
    async def _process_response(
        self,
        response: Any,
        method: str,
        params: dict,
        request_id: Any,
        user_id: str,
        is_llm_consuming: bool,
        quota_info: dict,
    ) -> Any:
        """Process response: track task trees and add quota info"""
        # Handle StreamingResponse (SSE mode) - return as-is
        if isinstance(response, StreamingResponse):
            return response
        
        # Extract result from JSONResponse
        result_dict = None
        if isinstance(response, JSONResponse):
            result_content = response.body
            if isinstance(result_content, bytes):
                try:
                    result_dict = json.loads(result_content.decode())
                except json.JSONDecodeError:
                    return response
            else:
                result_dict = result_content
        elif isinstance(response, dict):
            result_dict = response
        else:
            # Unknown response type, return as-is
            return response
        
        # Get actual result data (handle both JSON-RPC format and direct dict)
        actual_result = result_dict.get("result") if isinstance(result_dict, dict) and "result" in result_dict else result_dict
        
        # Get root_task_id from result
        root_task_id = None
        if method == "tasks.generate":
            if isinstance(actual_result, dict):
                root_task_id = actual_result.get("root_task_id")
                # Detect actual LLM-consuming from generated tasks
                generated_tasks = actual_result.get("tasks", [])
                if generated_tasks:
                    is_llm_consuming = detect_task_tree_from_tasks_array(generated_tasks)
        elif method == "tasks.execute":
            if isinstance(actual_result, dict):
                root_task_id = actual_result.get("root_task_id")
            task_id = params.get("task_id") or params.get("id")
            tasks = params.get("tasks")
            if not root_task_id:
                root_task_id = task_id
            
            # Only track if new task tree (not re-execution)
            # Re-execution: task_id exists and task already exists in DB, and no tasks array
            if root_task_id and not tasks:
                is_existing = await self._is_existing_task_tree(root_task_id)
                if is_existing:
                    # Re-execution - don't track
                    root_task_id = None
        
        # Start tracking for new task trees
        if root_task_id:
            await RateLimiter.start_task_tree(
                user_id=user_id,
                task_tree_id=root_task_id,
                is_llm_consuming=is_llm_consuming,
            )
        
        # Add quota info to response
        quota_info_dict = {
            "total_used": quota_info.get("total_count", 0) + (1 if root_task_id else 0),
            "total_limit": quota_info.get("total_limit"),
            "llm_used": quota_info.get("llm_count", 0) + (1 if is_llm_consuming and root_task_id else 0),
            "llm_limit": quota_info.get("llm_limit"),
        }
        
        # Update result with quota info
        if isinstance(actual_result, dict):
            actual_result["quota_info"] = quota_info_dict
        
        # Return updated response (preserve original format)
        if isinstance(response, JSONResponse):
            # Update the JSONResponse content
            if isinstance(result_dict, dict) and "result" in result_dict:
                result_dict["result"] = actual_result
            return JSONResponse(content=result_dict)
        else:
            # Return dict directly (if parent returns dict)
            return result_dict if isinstance(result_dict, dict) and "result" in result_dict else actual_result
    
    async def _is_existing_task_tree(self, task_id: str) -> bool:
        """Check if task tree already exists in database"""
        try:
            from apflow.core.storage import create_pooled_session
            from apflow.core.storage.sqlalchemy.task_repository import TaskRepository
            from apflow.core.config import get_task_model_class
            
            async with create_pooled_session() as db_session:
                task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
                task = await task_repository.get_task_by_id(task_id)
                return task is not None
        except Exception:
            return False
    
    def _get_reset_time(self) -> str:
        """Get quota reset time (midnight UTC)"""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return tomorrow.isoformat()

