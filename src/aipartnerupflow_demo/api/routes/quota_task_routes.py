"""
Quota-aware task routes wrapper

Wraps aipartnerupflow TaskRoutes to add quota checking and demo data fallback.

Uses aipartnerupflow v0.6.0 features:
- Automatic user_id extraction from JWT (with fallback to browser fingerprinting)
- Built-in demo mode via use_demo parameter
"""

from typing import Any, Optional
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException, status
import json
import os

from aipartnerupflow.api.routes.tasks import TaskRoutes
from aipartnerupflow_demo.extensions.rate_limiter import RateLimiter
from aipartnerupflow_demo.utils.header_utils import (
    has_llm_key_in_header,
    extract_user_id_from_request,
    extract_llm_key_from_header,
)
from aipartnerupflow_demo.utils.task_detection import (
    detect_task_tree_from_tasks_array,
    is_llm_consuming_task_tree_node,
)
from aipartnerupflow_demo.config.settings import settings
from aipartnerupflow.core.utils.logger import get_logger
from aipartnerupflow.core.types import TaskTreeNode
from aipartnerupflow.core.utils.helpers import tree_node_to_dict

logger = get_logger(__name__)


class QuotaTaskRoutes(TaskRoutes):
    """
    Quota-aware task routes wrapper
    
    Extends TaskRoutes to add:
    - Quota checking before task.generate and task.execute
    - Demo data fallback when quota exceeded
    - Task tree tracking
    """
    
    async def handle_task_requests(self, request: Request) -> JSONResponse:
        """Override to add quota checking for specific methods"""
        try:
            body = await request.json()
            method = body.get("method")
            params = body.get("params", {})
            
            # Extract user info
            # Priority: JWT (automatic from aipartnerupflow v0.6.0) > Cookie > Browser fingerprinting
            # extract_user_id_from_request now handles all fallbacks automatically
            user_id = extract_user_id_from_request(request)
            is_premium = has_llm_key_in_header(request)
            
            # Handle quota-checked methods
            if method == "tasks.generate":
                return await self._handle_task_generate_with_quota(
                    params, request, body.get("id"), user_id, is_premium
                )
            elif method == "tasks.execute":
                return await self._handle_task_execute_with_quota(
                    params, request, body.get("id"), user_id, is_premium
                )
            else:
                # For other methods, use parent implementation
                return await super().handle_task_requests(request)
                
        except Exception as e:
            logger.error(f"Error in quota task routes: {str(e)}", exc_info=True)
            # Fall back to parent implementation on error
            return await super().handle_task_requests(request)
    
    async def _handle_task_generate_with_quota(
        self,
        params: dict,
        request: Request,
        request_id: Any,
        user_id: str,
        is_premium: bool,
    ) -> JSONResponse:
        """Handle task.generate with quota checking"""
        try:
            # Assume LLM-consuming for task generation (always uses LLM)
            is_llm_consuming = True
            
            # Check quota
            allowed, quota_info = await RateLimiter.check_task_tree_quota(
                user_id=user_id,
                is_llm_consuming=is_llm_consuming,
                has_llm_key=is_premium,
            )
            
            if not allowed:
                if is_premium:
                    # Premium user exceeded quota - reject
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
                    # Free user - use built-in demo mode
                    logger.info(f"Free user {user_id} exceeded LLM quota, setting use_demo=True")
                    params["use_demo"] = True
                    # Continue with execution, aipartnerupflow will return demo data
            
            # Check concurrency limit
            concurrency_allowed, concurrency_info = await RateLimiter.check_concurrency_limit(user_id)
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
            
            # Store user_id and has_llm_key in params metadata for executor hooks
            # This allows executor hooks to access user info when tasks are created
            if "metadata" not in params:
                params["metadata"] = {}
            params["metadata"]["user_id"] = user_id
            params["metadata"]["has_llm_key"] = is_premium
            
            # Extract LLM API key from header and temporarily set it as environment variable
            # Note: While handle_task_generate() supports X-LLM-API-KEY header via LLMAPIKeyMiddleware,
            # executors (like GenerateExecutor) still need API key from environment variables when executing tasks.
            # This is because executors run in a different context and cannot access request context.
            llm_key_raw = extract_llm_key_from_header(request)
            original_openai_key = os.environ.get("OPENAI_API_KEY")
            original_anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
            
            try:
                # Temporarily set environment variable if LLM key is in header
                if llm_key_raw:
                    # Handle prefixed format: "openai:sk-..." or "anthropic:sk-ant-..."
                    # Also handle direct key format: "sk-..." or "sk-ant-..."
                    llm_key = llm_key_raw
                    is_anthropic = False
                    
                    if ":" in llm_key:
                        # Prefixed format: "openai:sk-..." or "anthropic:sk-ant-..."
                        prefix, key = llm_key.split(":", 1)
                        llm_key = key.strip()
                        is_anthropic = prefix.lower() == "anthropic"
                    else:
                        # Direct key format: detect from key prefix
                        # OpenAI keys typically start with "sk-", Anthropic keys start with "sk-ant-"
                        is_anthropic = llm_key.startswith("sk-ant-")
                    
                    if is_anthropic:
                        os.environ["ANTHROPIC_API_KEY"] = llm_key
                    else:
                        # Default to OpenAI format
                        os.environ["OPENAI_API_KEY"] = llm_key
                
                # Call parent implementation (returns dict, not JSONResponse)
                # Note: handle_task_generate() supports X-LLM-API-KEY header, but executors need env vars
                result_dict = await super().handle_task_generate(params, request, str(request_id) if request_id else "generate")
            finally:
                # Restore original environment variables
                if original_openai_key is not None:
                    os.environ["OPENAI_API_KEY"] = original_openai_key
                elif "OPENAI_API_KEY" in os.environ and llm_key_raw:
                    # Remove the temporary key if it wasn't there originally
                    del os.environ["OPENAI_API_KEY"]
                
                if original_anthropic_key is not None:
                    os.environ["ANTHROPIC_API_KEY"] = original_anthropic_key
                elif "ANTHROPIC_API_KEY" in os.environ and llm_key_raw:
                    # Remove the temporary key if it wasn't there originally
                    del os.environ["ANTHROPIC_API_KEY"]
            
            # Detect if actually LLM-consuming from generated tasks
            generated_tasks = result_dict.get("tasks", [])
            if generated_tasks:
                is_llm_consuming = detect_task_tree_from_tasks_array(generated_tasks)
            
            # Get root_task_id if saved
            # Note: root_task_id is only present if save=True
            root_task_id = result_dict.get("root_task_id")
            if root_task_id:
                # Start tracking for saved task trees
                await RateLimiter.start_task_tree(
                    user_id=user_id,
                    task_tree_id=root_task_id,
                    is_llm_consuming=is_llm_consuming,
                )
            # Note: For unsaved task trees (save=False), tracking will start when they are executed
            
            # Add quota info to response
            result_dict["quota_info"] = {
                "total_used": quota_info.get("total_count", 0) + (1 if root_task_id else 0),
                "total_limit": quota_info.get("total_limit"),
                "llm_used": quota_info.get("llm_count", 0) + (1 if is_llm_consuming and root_task_id else 0),
                "llm_limit": quota_info.get("llm_limit"),
            }
            
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result_dict,
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in task.generate with quota: {str(e)}", exc_info=True)
            raise
    
    async def _handle_task_execute_with_quota(
        self,
        params: dict,
        request: Request,
        request_id: Any,
        user_id: str,
        is_premium: bool,
    ) -> JSONResponse:
        """Handle task.execute with quota checking"""
        try:
            task_id = params.get("task_id") or params.get("id")
            tasks = params.get("tasks")
            
            # Determine if LLM-consuming
            is_llm_consuming = False
            if tasks and isinstance(tasks, list):
                is_llm_consuming = detect_task_tree_from_tasks_array(tasks)
            elif task_id:
                # Need to check task from database
                # Need to check task from database
                from aipartnerupflow.core.storage import create_pooled_session
                from aipartnerupflow.core.storage.sqlalchemy.task_repository import TaskRepository
                from aipartnerupflow.core.config import get_task_model_class
                
                async with create_pooled_session() as db_session:
                    task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
                    task = await task_repository.get_task_by_id(task_id)
                    if task:
                        from aipartnerupflow_demo.utils.task_detection import is_llm_consuming_task
                        is_llm_consuming = is_llm_consuming_task(task)
            
            # Check quota (only for new task trees, not re-execution)
            # For execute, we check if this is a new task tree creation
            if tasks or (task_id and not await self._is_existing_task_tree(task_id)):
                allowed, quota_info = await RateLimiter.check_task_tree_quota(
                    user_id=user_id,
                    is_llm_consuming=is_llm_consuming,
                    has_llm_key=is_premium,
                )
                
                if not allowed:
                    if is_premium:
                        # Premium user exceeded quota - reject
                        return JSONResponse(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            content={
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {
                                    "code": -32001,
                                    "message": "Daily task tree quota exceeded",
                                    "data": quota_info,
                                },
                            },
                        )
                    else:
                        # Free user - check if should use demo data
                        if is_llm_consuming and quota_info.get("llm_quota_exceeded"):
                            # Use aipartnerupflow v0.6.0's built-in demo mode
                            # Set use_demo=True in params to trigger demo mode
                            if not params.get("use_demo"):
                                params["use_demo"] = True
                                logger.info(f"Setting use_demo=True for task {task_id} (quota exceeded)")
                            # Continue with execution - executor hooks will handle demo mode
            
            # Check concurrency limit
            concurrency_allowed, concurrency_info = await RateLimiter.check_concurrency_limit(user_id)
            if not concurrency_allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32002,
                            "message": "Concurrency limit reached",
                            "data": concurrency_info,
                        },
                    },
                )
            
            # Store user_id and has_llm_key in params metadata for executor hooks
            # This allows executor hooks to access user info
            if "metadata" not in params:
                params["metadata"] = {}
            params["metadata"]["user_id"] = user_id
            params["metadata"]["has_llm_key"] = is_premium
            
            # Extract LLM API key from header and temporarily set it as environment variable
            # Note: Same reason as in _handle_task_generate_with_quota - executors need env vars
            llm_key_raw = extract_llm_key_from_header(request)
            original_openai_key = os.environ.get("OPENAI_API_KEY")
            original_anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
            
            try:
                # Temporarily set environment variable if LLM key is in header
                if llm_key_raw:
                    # Handle prefixed format: "openai:sk-..." or "anthropic:sk-ant-..."
                    # Also handle direct key format: "sk-..." or "sk-ant-..."
                    llm_key = llm_key_raw
                    is_anthropic = False
                    
                    if ":" in llm_key:
                        # Prefixed format: "openai:sk-..." or "anthropic:sk-ant-..."
                        prefix, key = llm_key.split(":", 1)
                        llm_key = key.strip()
                        is_anthropic = prefix.lower() == "anthropic"
                    else:
                        # Direct key format: detect from key prefix
                        # OpenAI keys typically start with "sk-", Anthropic keys start with "sk-ant-"
                        is_anthropic = llm_key.startswith("sk-ant-")
                    
                    if is_anthropic:
                        os.environ["ANTHROPIC_API_KEY"] = llm_key
                    else:
                        # Default to OpenAI format
                        os.environ["OPENAI_API_KEY"] = llm_key
                
                # Call parent implementation (may return JSONResponse or StreamingResponse)
                result = await super().handle_task_execute(params, request, str(request_id) if request_id else "execute", request_id)
            finally:
                # Restore original environment variables
                if original_openai_key is not None:
                    os.environ["OPENAI_API_KEY"] = original_openai_key
                elif "OPENAI_API_KEY" in os.environ and llm_key_raw:
                    # Remove the temporary key if it wasn't there originally
                    del os.environ["OPENAI_API_KEY"]
                
                if original_anthropic_key is not None:
                    os.environ["ANTHROPIC_API_KEY"] = original_anthropic_key
                elif "ANTHROPIC_API_KEY" in os.environ and llm_key_raw:
                    # Remove the temporary key if it wasn't there originally
                    del os.environ["ANTHROPIC_API_KEY"]
            
            # Handle StreamingResponse (SSE mode) - return as-is
            from starlette.responses import StreamingResponse
            if isinstance(result, StreamingResponse):
                return result
            
            # Extract result from JSONResponse if needed
            if isinstance(result, JSONResponse):
                result_content = result.body
                if isinstance(result_content, bytes):
                    result_dict = json.loads(result_content.decode())
                else:
                    result_dict = result_content
            else:
                result_dict = result
            
            # Get root_task_id
            root_task_id = result_dict.get("root_task_id") or task_id
            if root_task_id and (tasks or not await self._is_existing_task_tree(root_task_id)):
                # Start tracking for new task trees
                await RateLimiter.start_task_tree(
                    user_id=user_id,
                    task_tree_id=root_task_id,
                    is_llm_consuming=is_llm_consuming,
                )
            
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result_dict,
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in task.execute with quota: {str(e)}", exc_info=True)
            raise
    
    async def _is_existing_task_tree(self, task_id: str) -> bool:
        """Check if task tree already exists in database"""
        try:
            from aipartnerupflow.core.storage import create_pooled_session
            from aipartnerupflow.core.storage.sqlalchemy.task_repository import TaskRepository
            from aipartnerupflow.core.config import get_task_model_class
            
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

