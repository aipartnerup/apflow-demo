"""
Detailed validation tests for executor demo task data

This test file focuses on validating the actual data structure and content
of created executor demo tasks to identify any data problems.
"""

import pytest
import asyncio
from typing import Dict, Any
from apflow_demo.services.executor_demo_init import ExecutorDemoInitService
from apflow.core.storage import create_pooled_session
from apflow.core.storage.sqlalchemy.task_repository import TaskRepository
from apflow.core.config import get_task_model_class
from apflow.core.extensions.executor_metadata import get_all_executor_metadata

# Import executors to ensure they are registered
try:
    import apflow.extensions.docker.docker_executor
    import apflow.extensions.stdio.command_executor
    import apflow.extensions.stdio.system_info_executor
    import apflow.extensions.http.rest_executor
    import apflow.extensions.ssh.ssh_executor
    import apflow.extensions.generate.generate_executor
    import apflow.extensions.apflow.api_executor
    import apflow.extensions.mcp.mcp_executor
    import apflow.extensions.grpc.grpc_executor
except ImportError as e:
    print(f"Warning: Failed to import some executors: {e}")


@pytest.fixture
def test_user_id():
    """Generate a test user ID"""
    return "test_user_detailed_validation_12345"


@pytest.mark.asyncio
async def test_task_data_structure_completeness(test_user_id):
    """Test that task data structure is complete and correct"""
    service = ExecutorDemoInitService()
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Get task repository
    async with create_pooled_session() as db_session:
        task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
        all_metadata = get_all_executor_metadata()
        
        # Validate each task
        for task_id in created_task_ids:
            task = await task_repository.get_task_by_id(task_id)
            
            assert task is not None, f"Task {task_id} should exist"
            
            # Check all critical fields exist and are not None
            critical_fields = ['id', 'name', 'user_id', 'schemas', 'inputs', 'status']
            for field in critical_fields:
                assert hasattr(task, field), f"Task {task_id} missing field: {field}"
                value = getattr(task, field)
                assert value is not None, f"Task {task_id} field '{field}' is None"
            
            # Validate schemas structure
            assert isinstance(task.schemas, dict), f"Task {task_id} schemas should be dict, got {type(task.schemas)}"
            assert 'method' in task.schemas, f"Task {task_id} schemas missing 'method' key"
            executor_id = task.schemas['method']
            assert executor_id in all_metadata, f"Task {task_id} executor_id '{executor_id}' not in metadata"
            
            # Validate inputs structure
            assert isinstance(task.inputs, dict), f"Task {task_id} inputs should be dict, got {type(task.inputs)}"
            
            # Validate task name starts with "Demo:"
            # Note: system_info_executor creates aggregate tasks with special names like "Demo: System Info Executor (Aggregate)"
            assert task.name.startswith("Demo:"), \
                f"Task {task_id} name should start with 'Demo:', got '{task.name}'"
            
            # Validate user_id
            assert task.user_id == test_user_id, \
                f"Task {task_id} user_id mismatch: expected '{test_user_id}', got '{task.user_id}'"
            
            # Validate status
            assert task.status == "pending", \
                f"Task {task_id} status should be 'pending', got '{task.status}'"


@pytest.mark.asyncio
async def test_task_inputs_validation(test_user_id):
    """Test that task inputs are valid according to executor schema"""
    service = ExecutorDemoInitService()
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Get task repository
    async with create_pooled_session() as db_session:
        task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
        all_metadata = get_all_executor_metadata()
        
        # Validate inputs for each task
        for task_id in created_task_ids:
            task = await task_repository.get_task_by_id(task_id)
            
            assert task is not None
            executor_id = task.schemas['method']
            executor_metadata = all_metadata.get(executor_id)
            
            if not executor_metadata:
                pytest.fail(f"Executor metadata not found for {executor_id}")
            
            input_schema = executor_metadata.get('input_schema', {})
            if not input_schema:
                # If no input schema, inputs should be empty dict
                assert task.inputs == {}, \
                    f"Task {task_id} has inputs but executor has no input_schema: {task.inputs}"
                continue
            
            properties = input_schema.get('properties', {})
            required = input_schema.get('required', [])
            
            # Skip required field check for aggregate tasks (they have no inputs)
            # Aggregate tasks use aggregate_results_executor which doesn't require inputs
            if executor_id == 'aggregate_results_executor' and task.inputs == {}:
                continue
            
            # Check required fields are present
            missing_required = [field for field in required if field not in task.inputs]
            assert len(missing_required) == 0, \
                f"Task {task_id} missing required input fields: {missing_required}"
            
            # Check all input keys are valid schema fields
            # Exclude _demo_* fields as they are internal demo metadata, not executor inputs
            invalid_keys = [
                key for key in task.inputs.keys() 
                if key not in properties and key not in required and not key.startswith('_demo_')
            ]
            assert len(invalid_keys) == 0, \
                f"Task {task_id} has invalid input keys not in schema: {invalid_keys}"
            
            # Validate input value types match schema
            for input_key, input_value in task.inputs.items():
                if input_key in properties:
                    property_schema = properties[input_key]
                    expected_type = property_schema.get('type')
                    
                    if expected_type == 'string':
                        assert isinstance(input_value, str), \
                            f"Task {task_id} input '{input_key}' should be string, got {type(input_value)}"
                    elif expected_type == 'integer':
                        assert isinstance(input_value, int), \
                            f"Task {task_id} input '{input_key}' should be integer, got {type(input_value)}"
                    elif expected_type == 'number':
                        assert isinstance(input_value, (int, float)), \
                            f"Task {task_id} input '{input_key}' should be number, got {type(input_value)}"
                    elif expected_type == 'boolean':
                        assert isinstance(input_value, bool), \
                            f"Task {task_id} input '{input_key}' should be boolean, got {type(input_value)}"
                    elif expected_type == 'array':
                        assert isinstance(input_value, list), \
                            f"Task {task_id} input '{input_key}' should be array, got {type(input_value)}"
                    elif expected_type == 'object':
                        assert isinstance(input_value, dict), \
                            f"Task {task_id} input '{input_key}' should be object, got {type(input_value)}"


@pytest.mark.asyncio
async def test_task_id_uniqueness_and_format(test_user_id):
    """Test that task IDs are unique and follow correct format"""
    service = ExecutorDemoInitService()
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Check uniqueness
    unique_ids = set(created_task_ids)
    assert len(unique_ids) == len(created_task_ids), \
        f"Found duplicate task IDs. Total: {len(created_task_ids)}, Unique: {len(unique_ids)}"
    
    # Check format: demo_executor_{user_id[:8]}_{executor_id}_{timestamp}_{index}
    # Note: system_info_executor creates additional tasks with _parent, _child_0, etc. suffixes
    all_metadata = get_all_executor_metadata()
    
    for task_id in created_task_ids:
        assert task_id.startswith("demo_executor_"), \
            f"Task ID {task_id} should start with 'demo_executor_'"
        
        # Split by '_' to get parts
        parts = task_id.split("_")
        assert len(parts) >= 5, \
            f"Task ID {task_id} should have at least 5 parts separated by '_'"
        
        # Check user prefix (3rd part, index 2)
        user_prefix_actual = parts[2].replace("-", "_")
        assert user_prefix_actual == test_user_id[:8] or user_prefix_actual.startswith(test_user_id[:8]) or test_user_id[:8].startswith(user_prefix_actual), \
            f"Task ID {task_id} user prefix mismatch: expected '{test_user_id[:8]}', got '{user_prefix_actual}'"
        
        # Check executor_id exists in metadata (4th part, index 3)
        executor_id_safe = parts[3].replace("-", "_")
        
        # Try to find executor_id in metadata
        executor_id = None
        if executor_id_safe in all_metadata:
            executor_id = executor_id_safe
        else:
            for meta_executor_id in all_metadata.keys():
                if meta_executor_id.replace("_", "-") == parts[3]:
                    executor_id = meta_executor_id
                    break
        
        assert executor_id is not None and executor_id in all_metadata, \
            f"Task ID {task_id} executor_id '{executor_id_safe}' (from '{parts[3]}') not found in metadata. Parts: {parts}"
        
        # Check timestamp is numeric (find the numeric part)
        # For regular tasks: demo_executor_{user}_{executor}_{timestamp}_{index}
        # For aggregate tasks: demo_executor_{user}_{executor}_{timestamp}_{index}_parent or _child_N
        has_valid_timestamp = False
        for i, part in enumerate(parts[4:], start=4):
            if part.isdigit() and len(part) > 6:  # Timestamp should be long numeric
                has_valid_timestamp = True
                break
        
        assert has_valid_timestamp, \
            f"Task ID {task_id} should have a numeric timestamp part"


@pytest.mark.asyncio
async def test_all_executors_have_demo_tasks(test_user_id):
    """Test that demo tasks exist for all available executors"""
    service = ExecutorDemoInitService()
    
    # Get all executor metadata
    all_metadata = get_all_executor_metadata()
    
    if not all_metadata:
        pytest.skip("No executors available to test")
    
    # Initialize demo tasks (will skip if already exist)
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    # Get task repository to check all tasks for this user
    async with create_pooled_session() as db_session:
        from sqlalchemy import select
        
        TaskModel = get_task_model_class()
        task_repository = TaskRepository(db_session, task_model_class=TaskModel)
        
        # Query all demo tasks for this user (not just newly created ones)
        stmt = select(TaskModel).where(TaskModel.user_id == test_user_id)
        result = db_session.execute(stmt)
        user_tasks = result.scalars().all()
        
        # Filter demo tasks (name starts with "Demo:")
        demo_tasks = [task for task in user_tasks if task.name and task.name.startswith("Demo:")]
        
        # Check each executor has at least one corresponding demo task
        executor_ids_in_tasks = set()
        for task in demo_tasks:
            if task.schemas and isinstance(task.schemas, dict):
                executor_id = task.schemas.get("method")
                if executor_id:
                    executor_ids_in_tasks.add(executor_id)
        
        # Check all executors are represented (either newly created or already existed)
        missing_executors = set(all_metadata.keys()) - executor_ids_in_tasks
        assert len(missing_executors) == 0, \
            f"Missing demo tasks for executors: {missing_executors}. " \
            f"Created: {len(created_task_ids)}, Existing: {len(executor_ids_in_tasks)}"
        
        # Verify we have at least one task per executor
        # Note: system_info_executor creates multiple tasks (parent + children)
        assert len(executor_ids_in_tasks) == len(all_metadata), \
            f"Expected demo tasks for all {len(all_metadata)} executors, " \
            f"found tasks for {len(executor_ids_in_tasks)} executors"
