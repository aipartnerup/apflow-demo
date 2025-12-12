"""
Executor demo tasks initialization service

Creates demo tasks for all executors based on executor_metadata.
Each executor gets a demo task with inputs generated from its input_schema.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from aipartnerupflow.core.extensions.executor_metadata import get_all_executor_metadata
from aipartnerupflow.core.storage import get_default_session
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
            
            db_session = get_default_session()
            task_repository = TaskRepository(
                db_session, task_model_class=get_task_model_class()
            )
            
            created_task_ids: List[str] = []
            timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
            
            # Create demo task for each executor
            for executor_id, metadata in all_metadata.items():
                try:
                    executor_name = metadata.get("name", executor_id)
                    executor_description = metadata.get("description", "")
                    input_schema = metadata.get("input_schema", {})
                    
                    # Generate demo inputs from input_schema
                    demo_inputs = _generate_inputs_from_schema(input_schema)
                    
                    # Generate unique task ID
                    task_id = f"demo_executor_{user_id[:8]}_{executor_id}_{timestamp}"
                    
                    # Create task name
                    task_name = f"Demo: {executor_name}"
                    
                    # Create task data
                    task_data = {
                        "name": task_name,
                        "user_id": user_id,
                        "schemas": {"method": executor_id},
                        "inputs": demo_inputs,
                        "status": "pending",
                    }
                    
                    # Create the task
                    task = await task_repository.create_task(id=task_id, **task_data)
                    
                    # Commit the task
                    if task_repository.is_async:
                        await db_session.commit()
                        await db_session.refresh(task)
                    else:
                        db_session.commit()
                        db_session.refresh(task)
                    
                    created_task_ids.append(task_id)
                    logger.debug(
                        f"Created demo task for executor '{executor_id}': {task_id}"
                    )
                    
                except Exception as e:
                    logger.warning(
                        f"Failed to create demo task for executor '{executor_id}': {e}"
                    )
                    if task_repository.is_async:
                        await db_session.rollback()
                    else:
                        db_session.rollback()
                    continue
            
            logger.info(
                f"Initialized {len(created_task_ids)} executor demo tasks for user: {user_id[:20]}..."
            )
            return created_task_ids
            
        except Exception as e:
            logger.error(
                f"Error initializing executor demo tasks for user {user_id[:20] if user_id else 'unknown'}: {e}",
                exc_info=True,
            )
            raise

