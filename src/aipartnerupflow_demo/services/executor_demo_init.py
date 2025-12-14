"""
Executor demo tasks initialization service

Creates demo tasks for all executors based on executor_metadata.
Each executor gets a demo task with inputs generated from its input_schema.
For system_info_executor, creates an aggregate task with child tasks for cpu, memory, and disk.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import asyncio
from aipartnerupflow.core.extensions.executor_metadata import get_all_executor_metadata
from aipartnerupflow.core.storage import get_default_session, create_session
from aipartnerupflow.core.storage.sqlalchemy.task_repository import TaskRepository
from aipartnerupflow.core.config import get_task_model_class
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)


def _generate_default_value_from_schema(property_schema: Dict[str, Any]) -> Any:
    """
    Generate a default value from a JSON schema property
    
    Args:
        property_schema: JSON schema property definition
        
    Returns:
        Default value based on schema type
    """
    schema_type = property_schema.get("type")
    default = property_schema.get("default")
    
    # If default is provided, use it
    if default is not None:
        return default
    
    # Generate based on type
    if schema_type == "string":
        # Check for enum
        if "enum" in property_schema:
            return property_schema["enum"][0]
        # Check for examples
        if "examples" in property_schema and property_schema["examples"]:
            return property_schema["examples"][0]
        # Use description or name as hint
        description = property_schema.get("description", "")
        if "url" in description.lower() or "endpoint" in description.lower():
            return "https://example.com"
        elif "email" in description.lower():
            return "demo@example.com"
        elif "path" in description.lower() or "file" in description.lower():
            return "/tmp/demo.txt"
        else:
            return "demo_value"
    
    elif schema_type == "integer":
        return property_schema.get("minimum", 0) or 0
    
    elif schema_type == "number":
        return float(property_schema.get("minimum", 0.0) or 0.0)
    
    elif schema_type == "boolean":
        return False
    
    elif schema_type == "array":
        return []
    
    elif schema_type == "object":
        return {}
    
    # Default fallback
    return None


def _generate_inputs_from_schema(input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate demo inputs from executor's input_schema
    
    Args:
        input_schema: Executor's input schema (JSON schema format)
        
    Returns:
        Dictionary of demo inputs
    """
    if not input_schema or input_schema.get("type") != "object":
        return {}
    
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    inputs = {}
    
    # Generate values for all required fields and some optional ones
    fields_to_generate = set(required)
    # Also include first few optional fields for better demo
    optional_fields = [k for k in properties.keys() if k not in required]
    fields_to_generate.update(optional_fields[:3])  # Include up to 3 optional fields
    
    for field_name in fields_to_generate:
        if field_name in properties:
            field_schema = properties[field_name]
            inputs[field_name] = _generate_default_value_from_schema(field_schema)
    
    return inputs


def _generate_demo_task_for_system_info_executor(
    executor_id: str,
    executor_name: str,
    user_id: str,
    base_timestamp: int,
    task_index: int
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Generate aggregate task for system_info_executor with cpu, memory, disk child tasks
    
    Returns:
        Tuple of (tasks_data list, created_task_ids list)
    """
    user_prefix = user_id[:8].replace("_", "-")
    executor_id_safe = executor_id.replace("_", "-")
    
    # Create child tasks for cpu, memory, disk
    child_tasks = []
    child_task_ids = []
    resources = ["cpu", "memory", "disk"]
    
    for idx, resource in enumerate(resources):
        child_task_id = f"demo_executor_{user_prefix}_{executor_id_safe}_{base_timestamp}_{task_index}_child_{idx}"
        child_task = {
            "id": child_task_id,
            "name": f"Demo: {executor_name} - {resource.upper()}",
            "user_id": user_id,
            "schemas": {"method": executor_id},
            "inputs": {"resource": resource},
            "status": "pending",
            "parent_id": None,  # Will be set after parent is created
            "has_children": False,
        }
        child_tasks.append(child_task)
        child_task_ids.append(child_task_id)
    
    # Create parent aggregate task
    parent_task_id = f"demo_executor_{user_prefix}_{executor_id_safe}_{base_timestamp}_{task_index}_parent"
    # Set dependencies: parent task depends on all child tasks
    dependencies = [{"id": child_id, "required": True} for child_id in child_task_ids]
    parent_task = {
        "id": parent_task_id,
        "name": f"Demo: {executor_name} (Aggregate)",
        "user_id": user_id,
        "schemas": {"method": "aggregate_results_executor"},
        "inputs": {},  # Will be populated with dependency results by TaskManager
        "status": "pending",
        "parent_id": None,
        "has_children": True,
        "dependencies": dependencies,
    }
    
    # Set parent_id for child tasks
    for child_task in child_tasks:
        child_task["parent_id"] = parent_task_id
    
    # Combine all tasks (parent first, then children)
    all_tasks = [parent_task] + child_tasks
    all_task_ids = [parent_task_id] + child_task_ids
    
    return all_tasks, all_task_ids


def _generate_demo_task_for_executor(
    executor_id: str,
    executor_name: str,
    metadata: Dict[str, Any],
    user_id: str,
    base_timestamp: int,
    task_index: int
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Generate demo task(s) for a specific executor
    
    Args:
        executor_id: Executor ID
        executor_name: Executor name
        metadata: Executor metadata
        user_id: User ID
        base_timestamp: Base timestamp for task ID generation
        task_index: Task index for unique ID generation
        
    Returns:
        Tuple of (tasks_data list, created_task_ids list)
    """
    # Special handling for system_info_executor - create aggregate task
    if executor_id == "system_info_executor":
        return _generate_demo_task_for_system_info_executor(
            executor_id, executor_name, user_id, base_timestamp, task_index
        )
    
    # For other executors, generate inputs based on their specific requirements
    input_schema = metadata.get("input_schema", {})
    demo_inputs = {}
    
    # Generate inputs based on executor-specific logic
    if executor_id == "command_executor":
        demo_inputs = {"command": "echo 'Hello from demo'"}
    elif executor_id == "rest_executor":
        demo_inputs = {
            "url": "https://jsonplaceholder.typicode.com/posts/1",
            "method": "GET"
        }
    elif executor_id == "generate_executor":
        demo_inputs = {
            "requirement": "Get system information and display it"
        }
    elif executor_id == "docker_executor":
        demo_inputs = {
            "image": "alpine:latest",
            "command": "echo 'Hello from Docker'"
        }
    elif executor_id == "ssh_executor":
        demo_inputs = {
            "host": "example.com",
            "username": "demo_user",
            "command": "echo 'Hello from SSH'",
            "password": "demo_password"  # Demo only
        }
    elif executor_id == "mcp_executor":
        demo_inputs = {
            "transport": "stdio",
            "command": ["python", "-m", "mcp_server"],
            "operation": "list_tools"
        }
    elif executor_id == "websocket_executor":
        demo_inputs = {
            "url": "ws://echo.websocket.org",
            "message": "Hello WebSocket"
        }
    elif executor_id == "grpc_executor":
        demo_inputs = {
            "server": "localhost:50051",
            "service": "Greeter",
            "method": "SayHello",
            "request": {"name": "Demo"}
        }
    elif executor_id == "apflow_api_executor":
        demo_inputs = {
            "base_url": "http://localhost:8000",
            "method": "tasks.get",
            "params": {"task_id": "demo-task-123"}
        }
    elif executor_id == "aggregate_results_executor":
        # For aggregate_results_executor, inputs will be populated by TaskManager
        demo_inputs = {}
    else:
        # Fallback: use schema-based generation
        demo_inputs = _generate_inputs_from_schema(input_schema)
    
    # Generate unique task ID
    user_prefix = user_id[:8].replace("_", "-")
    executor_id_safe = executor_id.replace("_", "-")
    task_id = f"demo_executor_{user_prefix}_{executor_id_safe}_{base_timestamp}_{task_index}"
    
    # Create task name
    task_name = f"Demo: {executor_name}"
    
    # Prepare task data
    task_data = {
        "id": task_id,
        "name": task_name,
        "user_id": user_id,
        "schemas": {"method": executor_id},
        "inputs": demo_inputs,
        "status": "pending",
        "parent_id": None,
        "has_children": False,
    }
    
    return [task_data], [task_id]


class ExecutorDemoInitService:
    """Service for initializing demo tasks for all executors"""

    async def init_all_executor_demo_tasks_for_user(self, user_id: str) -> List[str]:
        """
        Initialize demo tasks for all executors for a specific user
        
        Creates one demo task per executor based on executor_metadata:
        - Uses executor_id as schemas.method
        - Generates demo inputs from executor's input_schema
        - Sets task name based on executor name
        - Sets user_id
        
        These tasks are independent (not part of the same task tree), so they are created
        using batch insert for better performance and to avoid database connection conflicts.
        All tasks are created in a single transaction for efficiency.
        
        Args:
            user_id: User ID to create tasks for
            
        Returns:
            List of created task IDs
        """
        try:
            # Get all executor metadata
            all_metadata = get_all_executor_metadata()
            
            if not all_metadata:
                logger.warning("No executor metadata found")
                return []
            
            base_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
            TaskModel = get_task_model_class()
            
            # Use default session but ensure it's in a clean state
            # For batch operations, we'll use add_all and commit to avoid conflicts
            db_session = get_default_session()
            task_repository = TaskRepository(db_session, task_model_class=TaskModel)
            is_async = task_repository.is_async
            
            # Prepare all task data as dictionaries (no database operations)
            # Using dictionaries allows us to use bulk_insert_mappings which bypasses ORM flush
            tasks_data = []
            created_task_ids = []
            
            for task_index, (executor_id, metadata) in enumerate(all_metadata.items()):
                try:
                    executor_name = metadata.get("name", executor_id)
                    
                    # Use specialized generator for each executor
                    executor_tasks, executor_task_ids = _generate_demo_task_for_executor(
                        executor_id=executor_id,
                        executor_name=executor_name,
                        metadata=metadata,
                        user_id=user_id,
                        base_timestamp=base_timestamp,
                        task_index=task_index
                    )
                    
                    tasks_data.extend(executor_tasks)
                    created_task_ids.extend(executor_task_ids)
                    
                except Exception as e:
                    logger.warning(
                        f"Failed to prepare demo task for executor '{executor_id}': {e}",
                        exc_info=True
                    )
                    continue
            
            if not tasks_data:
                return []
            
            # Use raw SQL text to bypass ORM completely and avoid connection conflicts
            # Insert tasks one by one using raw SQL to avoid asyncpg concurrency issues
            try:
                from sqlalchemy import text
                import json
                
                if is_async:
                    # For async, insert tasks one by one using raw SQL text
                    # This avoids ORM flush and transaction conflicts
                    if not tasks_data:
                        return []
                    
                    # Ensure session is clean before starting
                    # Clear any pending operations and expire all objects
                    try:
                        db_session.expire_all()
                        # Small delay to let event loop process any pending operations
                        import asyncio
                        await asyncio.sleep(0)
                    except Exception:
                        # Ignore errors during cleanup
                        pass
                    
                    # Get table name from model
                    table_name = TaskModel.__table__.name
                    
                    # Insert each task individually using raw SQL
                    # Don't use explicit begin() as session may already be in a transaction
                    # SQLAlchemy will handle transaction management automatically
                    for task_data in tasks_data:
                        try:
                            # Serialize JSON fields
                            inputs_json = json.dumps(task_data.get("inputs", {}))
                            schemas_json = json.dumps(task_data.get("schemas", {}))
                            
                            # Extract task fields
                            task_id = task_data.get("id")
                            task_user_id = task_data.get("user_id")
                            task_name = task_data.get("name")
                            task_status = task_data.get("status", "pending")
                            task_parent_id = task_data.get("parent_id")
                            task_has_children = task_data.get("has_children", False)
                            task_dependencies = task_data.get("dependencies")
                            
                            # Serialize dependencies JSON
                            dependencies_json = json.dumps(task_dependencies) if task_dependencies else None
                            
                            # Build INSERT statement with bound parameters
                            # Use CAST to avoid parameter placeholder conflicts with ::json syntax
                            # Include parent_id, has_children, and dependencies for task tree support
                            sql = text(f"""
                                INSERT INTO {table_name} (id, user_id, name, status, inputs, schemas, priority, progress, has_children, has_copy, parent_id, dependencies)
                                VALUES (:id, :user_id, :name, :status, CAST(:inputs AS json), CAST(:schemas AS json), 2, 0.0, :has_children, false, :parent_id, CAST(:dependencies AS json))
                            """)
                            
                            # Execute with parameters
                            await db_session.execute(
                                sql,
                                {
                                    "id": task_id,
                                    "user_id": task_user_id,
                                    "name": task_name,
                                    "status": task_status,
                                    "inputs": inputs_json,
                                    "schemas": schemas_json,
                                    "has_children": task_has_children,
                                    "parent_id": task_parent_id,
                                    "dependencies": dependencies_json,
                                }
                            )
                        except Exception as insert_error:
                            # Log error and remove from created_task_ids
                            logger.warning(
                                f"Failed to insert task {task_data.get('id', 'unknown')}: {insert_error}"
                            )
                            if task_data["id"] in created_task_ids:
                                created_task_ids.remove(task_data["id"])
                            # Continue with next task
                            continue
                    
                    # Commit all inserts in a single transaction
                    # Use retry mechanism to handle concurrent operation conflicts
                    import asyncio
                    max_retries = 3
                    retry_delay = 0.2  # 200ms delay between retries
                    
                    for attempt in range(max_retries):
                        try:
                            # Clear session state to avoid conflicts with previous operations
                            db_session.expire_all()
                            # Delay to let event loop process any pending operations from previous tests
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            # Now commit
                            await db_session.commit()
                            # Success! Break out of retry loop
                            break
                        except Exception as commit_error:
                            # Check if it's a concurrency error that we can retry
                            error_str = str(commit_error)
                            is_retryable = (
                                "another operation is in progress" in error_str or
                                "cannot perform operation" in error_str
                            )
                            
                            if is_retryable and attempt < max_retries - 1:
                                # Retryable error and we have retries left
                                logger.debug(
                                    f"Commit failed (attempt {attempt + 1}/{max_retries}), retrying: {commit_error}"
                                )
                                # Try to rollback to clean state before retry
                                try:
                                    await db_session.rollback()
                                except Exception:
                                    pass
                                continue
                            else:
                                # Non-retryable error or out of retries
                                logger.warning(
                                    f"Failed to commit batch insert after {attempt + 1} attempts: {commit_error}"
                                )
                                try:
                                    await db_session.rollback()
                                except Exception:
                                    pass
                                created_task_ids.clear()
                                raise
                else:
                    # For sync, use bulk_insert_mappings which is more efficient
                    db_session.bulk_insert_mappings(TaskModel, tasks_data)
                    db_session.commit()
                
                logger.debug(f"Batch created {len(tasks_data)} demo tasks")
                
            except Exception as e:
                logger.error(
                    f"Failed to batch create demo tasks: {e}",
                    exc_info=True
                )
                # Rollback on error
                try:
                    if is_async:
                        await db_session.rollback()
                    else:
                        db_session.rollback()
                except Exception as rollback_err:
                    # Ignore rollback errors to avoid masking the original error
                    logger.debug(f"Rollback error (ignored): {rollback_err}")
                # Return empty list on failure
                return []
            
            logger.info(
                f"Initialized {len(created_task_ids)}/{len(all_metadata)} executor demo tasks for user: {user_id[:20]}..."
            )
            return created_task_ids
            
        except Exception as e:
            logger.error(
                f"Error initializing executor demo tasks for user {user_id[:20] if user_id else 'unknown'}: {e}",
                exc_info=True,
            )
            raise

