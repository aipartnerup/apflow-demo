"""
Detailed validation tests for executor demo task data

This test file focuses on validating the actual data structure and content
of created executor demo tasks to identify any data problems.
"""

import pytest
import asyncio
from typing import Dict, Any
from aipartnerupflow_demo.services.executor_demo_init import ExecutorDemoInitService
from aipartnerupflow.core.storage import get_default_session
from aipartnerupflow.core.storage.sqlalchemy.task_repository import TaskRepository
from aipartnerupflow.core.config import get_task_model_class
from aipartnerupflow.core.extensions.executor_metadata import get_all_executor_metadata


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
    db_session = get_default_session()
    task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
    all_metadata = get_all_executor_metadata()
    
    # Validate each task
    for task_id in created_task_ids:
        if task_repository.is_async:
            task = await task_repository.get_task_by_id(task_id)
        else:
            task = task_repository.get_task_by_id(task_id)
        
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
        
        # Validate executor metadata matches
        executor_metadata = all_metadata[executor_id]
        executor_name = executor_metadata.get('name', executor_id)
        assert task.name == f"Demo: {executor_name}", \
            f"Task {task_id} name mismatch: expected 'Demo: {executor_name}', got '{task.name}'"
        
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
    db_session = get_default_session()
    task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
    all_metadata = get_all_executor_metadata()
    
    # Validate inputs for each task
    for task_id in created_task_ids:
        if task_repository.is_async:
            task = await task_repository.get_task_by_id(task_id)
        else:
            task = task_repository.get_task_by_id(task_id)
        
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
        
        # Check required fields are present
        missing_required = [field for field in required if field not in task.inputs]
        assert len(missing_required) == 0, \
            f"Task {task_id} missing required input fields: {missing_required}"
        
        # Check all input keys are valid schema fields
        invalid_keys = [key for key in task.inputs.keys() if key not in properties and key not in required]
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
    user_prefix = test_user_id[:8]
    all_metadata = get_all_executor_metadata()
    
    for task_id in created_task_ids:
        assert task_id.startswith("demo_executor_"), \
            f"Task ID {task_id} should start with 'demo_executor_'"
        
        # Split by '_' to get parts
        parts = task_id.split("_")
        assert len(parts) >= 5, \
            f"Task ID {task_id} should have at least 5 parts separated by '_'"
        
        # Format: demo_executor_{user_prefix}_{executor_id}_{timestamp}_{index}
        # user_prefix and executor_id use '-' instead of '_', so we need to handle that
        # parts[0] = 'demo', parts[1] = 'executor', parts[2] = user_prefix, parts[3] = executor_id, parts[-2] = timestamp, parts[-1] = index
        
        # Check user prefix (3rd part, index 2)
        user_prefix_actual = parts[2].replace("-", "_")
        assert user_prefix_actual == test_user_id[:8] or user_prefix_actual.startswith(test_user_id[:8]) or test_user_id[:8].startswith(user_prefix_actual), \
            f"Task ID {task_id} user prefix mismatch: expected '{test_user_id[:8]}', got '{user_prefix_actual}'"
        
        # Check executor_id exists in metadata (4th part, index 3)
        # Executor ID uses '-' instead of '_' in task_id, so convert back
        executor_id_safe = parts[3].replace("-", "_")
        
        # Try to find executor_id in metadata
        executor_id = None
        if executor_id_safe in all_metadata:
            executor_id = executor_id_safe
        else:
            # Try to match by checking if any executor_id matches when we replace '-' with '_'
            for meta_executor_id in all_metadata.keys():
                if meta_executor_id.replace("_", "-") == parts[3]:
                    executor_id = meta_executor_id
                    break
        
        assert executor_id is not None and executor_id in all_metadata, \
            f"Task ID {task_id} executor_id '{executor_id_safe}' (from '{parts[3]}') not found in metadata. Parts: {parts}"
        
        # Check timestamp is numeric (second to last part)
        timestamp = parts[-2]
        assert timestamp.isdigit(), \
            f"Task ID {task_id} timestamp '{timestamp}' should be numeric"
        
        # Check index is numeric (last part)
        index = parts[-1]
        assert index.isdigit(), \
            f"Task ID {task_id} index '{index}' should be numeric"


@pytest.mark.asyncio
async def test_all_executors_have_demo_tasks(test_user_id):
    """Test that demo tasks are created for all available executors"""
    service = ExecutorDemoInitService()
    
    # Get all executor metadata
    all_metadata = get_all_executor_metadata()
    
    if not all_metadata:
        pytest.skip("No executors available to test")
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    # Check count matches
    assert len(created_task_ids) == len(all_metadata), \
        f"Expected {len(all_metadata)} tasks, got {len(created_task_ids)}"
    
    # Get task repository
    db_session = get_default_session()
    task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
    
    # Check each executor has a corresponding task
    executor_ids_in_tasks = set()
    for task_id in created_task_ids:
        if task_repository.is_async:
            task = await task_repository.get_task_by_id(task_id)
        else:
            task = task_repository.get_task_by_id(task_id)
        
        assert task is not None
        executor_id = task.schemas['method']
        executor_ids_in_tasks.add(executor_id)
    
    # Check all executors are represented
    missing_executors = set(all_metadata.keys()) - executor_ids_in_tasks
    assert len(missing_executors) == 0, \
        f"Missing demo tasks for executors: {missing_executors}"

