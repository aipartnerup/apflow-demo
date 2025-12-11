"""
Demo task initialization service

Creates demo tasks for specific users, similar to init_examples_data but user-specific.
"""

from typing import List, Any
from datetime import datetime, timezone, timedelta
from aipartnerupflow.examples.data import get_example_tasks
from aipartnerupflow.core.storage import get_default_session
from aipartnerupflow.core.storage.sqlalchemy.task_repository import TaskRepository
from aipartnerupflow.core.config import get_task_model_class
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)


class DemoInitService:
    """Service for initializing demo tasks for users"""

    async def init_demo_tasks_for_user(self, user_id: str) -> List[str]:
        """
        Initialize demo tasks for a specific user
        
        Creates demo tasks similar to init_examples_data() but:
        - Uses provided user_id instead of EXAMPLE_USER_ID
        - Generates unique task IDs (timestamp-based to avoid conflicts)
        - All tasks belong to the current user
        
        Args:
            user_id: User ID to create tasks for
            
        Returns:
            List of created task IDs
        """
        try:
            db_session = get_default_session()
            task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
            
            # Get example task definitions
            example_tasks = get_example_tasks()
            
            # Generate unique prefix for this user's demo tasks
            # Use timestamp to ensure uniqueness
            timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
            task_id_prefix = f"demo_{user_id[:8]}_{timestamp}"
            
            # Create a mapping from original task IDs to new task IDs
            # This is needed to update parent_id and dependencies
            task_id_mapping: dict[str, str] = {}
            
            # First pass: Create all tasks with mapped IDs but without parent_id/dependencies
            # Store original values for second pass
            task_updates: List[dict] = []  # Store updates needed after creation
            created_task_ids: List[str] = []
            created_tasks: dict[str, Any] = {}  # Map new_task_id to task object
            now = datetime.now(timezone.utc)
            
            # Sort tasks: root tasks first, then children
            sorted_tasks = sorted(
                example_tasks, 
                key=lambda t: (t.get("parent_id") is not None, t.get("parent_id") or "")
            )
            
            # First pass: Create all tasks
            for task_data in sorted_tasks:
                try:
                    # Create a copy to avoid modifying the original
                    task_data_copy = task_data.copy()
                    
                    # Generate new unique task ID
                    original_id = task_data_copy.pop("id")
                    # Extract the base name from original ID (e.g., "example_root_001" -> "root_001")
                    base_name = original_id.replace("example_", "")
                    new_task_id = f"{task_id_prefix}_{base_name}"
                    task_id_mapping[original_id] = new_task_id
                    
                    # Store original parent_id and dependencies for second pass
                    original_parent_id = task_data_copy.get("parent_id")
                    original_dependencies = task_data_copy.get("dependencies", [])
                    
                    # Update user_id
                    task_data_copy["user_id"] = user_id
                    
                    # Temporarily remove parent_id and dependencies (will be set in second pass)
                    task_data_copy["parent_id"] = None
                    task_data_copy["dependencies"] = []
                    
                    # Extract fields that should be set directly on the model
                    status = task_data_copy.pop("status", "pending")
                    progress = task_data_copy.pop("progress", 0.0)
                    created_at = task_data_copy.pop("created_at", None) or (now - timedelta(hours=1))
                    started_at = task_data_copy.pop("started_at", None)
                    completed_at = task_data_copy.pop("completed_at", None)
                    result = task_data_copy.pop("result", None)
                    error = task_data_copy.pop("error", None)
                    
                    # Create the task
                    task = await task_repository.create_task(
                        id=new_task_id,
                        **task_data_copy
                    )
                    
                    # Update timestamps if provided
                    if created_at:
                        task.created_at = created_at
                    
                    # Commit the task
                    if task_repository.is_async:
                        await db_session.commit()
                        await db_session.refresh(task)
                    else:
                        db_session.commit()
                        db_session.refresh(task)
                    
                    created_task_ids.append(new_task_id)
                    created_tasks[new_task_id] = task
                    
                    # Store update info for second pass
                    task_updates.append({
                        "task": task,
                        "new_task_id": new_task_id,
                        "original_parent_id": original_parent_id,
                        "original_dependencies": original_dependencies,
                        "status": status,
                        "progress": progress,
                        "result": result,
                        "error": error,
                        "started_at": started_at,
                        "completed_at": completed_at,
                    })
                    
                    logger.debug(f"Created demo task: {task.id} ({task.name}) for user: {user_id[:20]}...")
                    
                except Exception as e:
                    logger.warning(f"Failed to create demo task {original_id}: {e}")
                    if task_repository.is_async:
                        await db_session.rollback()
                    else:
                        db_session.rollback()
                    continue
            
            # Second pass: Update parent_id, dependencies, and status
            for update_info in task_updates:
                try:
                    task = update_info["task"]
                    original_parent_id = update_info["original_parent_id"]
                    original_dependencies = update_info["original_dependencies"]
                    
                    # Update parent_id if needed
                    if original_parent_id and original_parent_id in task_id_mapping:
                        task.parent_id = task_id_mapping[original_parent_id]
                        # Update parent's has_children flag
                        parent_task = created_tasks.get(task_id_mapping[original_parent_id])
                        if parent_task:
                            parent_task.has_children = True
                    
                    # Update dependencies if needed
                    if original_dependencies:
                        updated_dependencies = []
                        for dep in original_dependencies:
                            dep_id = dep.get("id") if isinstance(dep, dict) else dep
                            if dep_id in task_id_mapping:
                                if isinstance(dep, dict):
                                    updated_dependencies.append({
                                        "id": task_id_mapping[dep_id],
                                        "required": dep.get("required", True)
                                    })
                                else:
                                    updated_dependencies.append(task_id_mapping[dep_id])
                        if updated_dependencies:
                            task.dependencies = updated_dependencies
                    
                    # Update status and other fields if needed
                    if update_info["status"] != "pending":
                        await task_repository.update_task_status(
                            task_id=task.id,
                            status=update_info["status"],
                            progress=update_info["progress"],
                            result=update_info["result"],
                            error=update_info["error"],
                            started_at=update_info["started_at"],
                            completed_at=update_info["completed_at"]
                        )
                    elif update_info["progress"] != 0.0:
                        # Update progress even if status is pending
                        await task_repository.update_task_status(
                            task_id=task.id,
                            status="pending",
                            progress=update_info["progress"]
                        )
                    
                    # Update timestamps if provided
                    if update_info["started_at"] and not task.started_at:
                        task.started_at = update_info["started_at"]
                    if update_info["completed_at"] and not task.completed_at:
                        task.completed_at = update_info["completed_at"]
                    
                    # Commit updates
                    if task_repository.is_async:
                        await db_session.commit()
                        await db_session.refresh(task)
                    else:
                        db_session.commit()
                        db_session.refresh(task)
                    
                except Exception as e:
                    logger.warning(f"Failed to update demo task {update_info['new_task_id']}: {e}")
                    if task_repository.is_async:
                        await db_session.rollback()
                    else:
                        db_session.rollback()
                    continue
            
            logger.info(f"Initialized {len(created_task_ids)} demo tasks for user: {user_id[:20]}...")
            return created_task_ids
            
        except Exception as e:
            logger.error(f"Error initializing demo tasks for user {user_id[:20] if user_id else 'unknown'}: {e}", exc_info=True)
            raise

