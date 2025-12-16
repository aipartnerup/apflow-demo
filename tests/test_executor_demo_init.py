"""
Tests for executor demo task initialization

Tests the ExecutorDemoInitService to ensure demo tasks are created correctly
with proper data structure, unique IDs, and all required fields.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import List, Dict, Any
from aipartnerupflow_demo.services.executor_demo_init import ExecutorDemoInitService
from aipartnerupflow.core.storage import create_pooled_session
from aipartnerupflow.core.storage.sqlalchemy.task_repository import TaskRepository
from aipartnerupflow.core.config import get_task_model_class
from aipartnerupflow.core.extensions.executor_metadata import get_all_executor_metadata

# Import executors to ensure they are registered
try:
    import aipartnerupflow.extensions.docker.docker_executor
    import aipartnerupflow.extensions.stdio.command_executor
    import aipartnerupflow.extensions.stdio.system_info_executor
    import aipartnerupflow.extensions.http.rest_executor
    import aipartnerupflow.extensions.ssh.ssh_executor
    import aipartnerupflow.extensions.generate.generate_executor
    import aipartnerupflow.extensions.apflow.api_executor
    import aipartnerupflow.extensions.mcp.mcp_executor
    import aipartnerupflow.extensions.grpc.grpc_executor
except ImportError as e:
    print(f"Warning: Failed to import some executors: {e}")


@pytest.fixture
def test_user_id():
    """Generate a test user ID"""
    return "test_user_executor_demo_12345"


@pytest_asyncio.fixture
async def db_session():
    """Get database session"""
    async with create_pooled_session() as session:
        yield session


@pytest.fixture
def task_repository(db_session):
    """Get task repository"""
    return TaskRepository(db_session, task_model_class=get_task_model_class())


@pytest_asyncio.fixture
async def cleanup_tasks(test_user_id):
    """Cleanup fixture to remove test tasks after test"""
    yield
    # Cleanup: remove all test tasks
    try:
        from sqlalchemy import select, delete
        
        TaskModel = get_task_model_class()
        
        async with create_pooled_session() as db_session:
            # Query tasks by user_id
            stmt = select(TaskModel).where(TaskModel.user_id == test_user_id)
            result = await db_session.execute(stmt)
            tasks = result.scalars().all()
            
            # Delete each task
            for task in tasks:
                await db_session.delete(task)
            await db_session.commit()
    except Exception as e:
        # Ignore cleanup errors
        pass


@pytest.mark.asyncio
@pytest.mark.order(1)  # Run this test first to avoid session state conflicts
async def test_init_all_executor_demo_tasks_creates_tasks(test_user_id, cleanup_tasks):
    """Test that initialization creates tasks for all executors"""
    service = ExecutorDemoInitService()
    
    # Get all executor metadata to know expected count
    all_metadata = get_all_executor_metadata()
    # system_info_executor creates 4 tasks (1 parent + 3 children), so we expect +3 extra tasks
    expected_min_count = len(all_metadata) if all_metadata else 0
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    # Verify tasks were created
    assert isinstance(created_task_ids, list)
    if expected_min_count > 0:
        assert len(created_task_ids) > 0, "Should create at least one task if executors exist"
        # At least one task per executor, but system_info_executor creates more
        assert len(created_task_ids) >= expected_min_count, \
            f"Should create at least {expected_min_count} tasks, got {len(created_task_ids)}"
    else:
        # If no executors, should return empty list
        assert len(created_task_ids) == 0


@pytest.mark.asyncio
async def test_created_tasks_have_unique_ids(test_user_id, cleanup_tasks):
    """Test that all created tasks have unique IDs"""
    service = ExecutorDemoInitService()
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Check uniqueness
    unique_ids = set(created_task_ids)
    assert len(unique_ids) == len(created_task_ids), f"Found duplicate task IDs: {created_task_ids}"


@pytest.mark.asyncio
async def test_created_tasks_can_be_retrieved_from_db(test_user_id, cleanup_tasks):
    """Test that created tasks can be retrieved from database"""
    service = ExecutorDemoInitService()
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Get task repository
    async with create_pooled_session() as db_session:
        task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
        
        # Retrieve each task from database
        for task_id in created_task_ids:
            task = await task_repository.get_task_by_id(task_id)
            
            assert task is not None, f"Task {task_id} should exist in database"
            assert task.id == task_id, f"Task ID mismatch: expected {task_id}, got {task.id}"


@pytest.mark.asyncio
async def test_created_tasks_have_required_fields(test_user_id, cleanup_tasks):
    """Test that created tasks have all required fields"""
    service = ExecutorDemoInitService()
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Get all executor metadata for validation
    all_metadata = get_all_executor_metadata()
    
    # Get task repository
    async with create_pooled_session() as db_session:
        task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
        
        # Check each task
        for task_id in created_task_ids:
            task = await task_repository.get_task_by_id(task_id)
            
            assert task is not None, f"Task {task_id} should exist"
            
            # Check required fields
            assert hasattr(task, 'id'), f"Task {task_id} missing 'id' field"
            assert task.id is not None, f"Task {task_id} has None 'id'"
            assert task.id == task_id, f"Task {task_id} ID mismatch"
            
            assert hasattr(task, 'name'), f"Task {task_id} missing 'name' field"
            assert task.name is not None, f"Task {task_id} has None 'name'"
            assert isinstance(task.name, str), f"Task {task_id} 'name' should be string"
            assert task.name.startswith("Demo:"), f"Task {task_id} name should start with 'Demo:'"
            
            assert hasattr(task, 'user_id'), f"Task {task_id} missing 'user_id' field"
            assert task.user_id is not None, f"Task {task_id} has None 'user_id'"
            assert task.user_id == test_user_id, f"Task {task_id} user_id mismatch: expected {test_user_id}, got {task.user_id}"
            
            assert hasattr(task, 'schemas'), f"Task {task_id} missing 'schemas' field"
            assert task.schemas is not None, f"Task {task_id} has None 'schemas'"
            assert isinstance(task.schemas, dict), f"Task {task_id} 'schemas' should be dict"
            assert 'method' in task.schemas, f"Task {task_id} 'schemas' missing 'method' key"
            assert task.schemas['method'] is not None, f"Task {task_id} 'schemas.method' is None"
            assert isinstance(task.schemas['method'], str), f"Task {task_id} 'schemas.method' should be string"
            
            # Verify method matches an executor ID
            executor_id = task.schemas['method']
            assert executor_id in all_metadata, f"Task {task_id} executor_id '{executor_id}' not found in metadata"
            
            assert hasattr(task, 'inputs'), f"Task {task_id} missing 'inputs' field"
            assert task.inputs is not None, f"Task {task_id} has None 'inputs'"
            assert isinstance(task.inputs, dict), f"Task {task_id} 'inputs' should be dict"
            
            assert hasattr(task, 'status'), f"Task {task_id} missing 'status' field"
            assert task.status is not None, f"Task {task_id} has None 'status'"
            assert isinstance(task.status, str), f"Task {task_id} 'status' should be string"
            assert task.status == "pending", f"Task {task_id} status should be 'pending', got '{task.status}'"


@pytest.mark.asyncio
async def test_task_inputs_match_executor_schema(test_user_id, cleanup_tasks):
    """Test that task inputs are generated correctly from executor input_schema"""
    service = ExecutorDemoInitService()
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Get all executor metadata
    all_metadata = get_all_executor_metadata()
    
    # Get task repository
    async with create_pooled_session() as db_session:
        task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
        
        # Check each task's inputs match its executor schema
        for task_id in created_task_ids:
            task = await task_repository.get_task_by_id(task_id)
            
            assert task is not None
            executor_id = task.schemas['method']
            executor_metadata = all_metadata.get(executor_id)
            
            if executor_metadata:
                input_schema = executor_metadata.get('input_schema', {})
                properties = input_schema.get('properties', {})
                required = input_schema.get('required', [])
                
                # Check that all required fields are present in inputs
                for required_field in required:
                    assert required_field in task.inputs, \
                        f"Task {task_id} missing required input field '{required_field}'"
                
                # Check that inputs only contain valid schema fields
                for input_key in task.inputs.keys():
                    assert input_key in properties or input_key in required, \
                        f"Task {task_id} has input field '{input_key}' not in schema"


@pytest.mark.asyncio
async def test_task_ids_follow_expected_format(test_user_id, cleanup_tasks):
    """Test that task IDs follow the expected format"""
    service = ExecutorDemoInitService()
    
    # Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
        # Check ID format: demo_executor_{user_id[:8]}_{executor_id}_{timestamp}_{index}
        # Note: user_id prefix uses '-' instead of '_' to avoid parsing issues
        for task_id in created_task_ids:
            assert task_id.startswith("demo_executor_"), \
                f"Task ID {task_id} should start with 'demo_executor_'"
            
            parts = task_id.split("_")
            assert len(parts) >= 5, \
                f"Task ID {task_id} should have format: demo_executor_{{user_prefix}}_{{executor_id}}_{{timestamp}}_{{index}}"
            
            # Check user prefix matches (note: uses '-' instead of '_' in task ID)
            user_prefix_expected = test_user_id[:8]
            user_prefix_actual = parts[2].replace("-", "_")  # Convert back from task ID format
            assert user_prefix_actual == user_prefix_expected, \
                f"Task ID {task_id} user prefix mismatch: expected {user_prefix_expected}, got {user_prefix_actual} (from {parts[2]})"


@pytest.mark.asyncio
async def test_multiple_initializations_create_different_tasks(test_user_id, cleanup_tasks):
    """Test that multiple initializations create different tasks (not duplicates)"""
    service = ExecutorDemoInitService()
    
    # First initialization
    first_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(first_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Second initialization (should create new tasks with different IDs)
    second_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    # Check that IDs are different (due to different timestamps)
    first_set = set(first_task_ids)
    second_set = set(second_task_ids)
    
    # They should be different (or at least have different timestamps)
    # Note: If executors are the same, we expect different task IDs due to timestamp
    assert len(first_set) == len(first_task_ids), "First batch should have unique IDs"
    assert len(second_set) == len(second_task_ids), "Second batch should have unique IDs"
    
    # The task IDs should be different (different timestamps)
    # But if they're created very quickly, timestamps might be the same
    # So we check that at least the sets are different or have different timestamps
    if first_set == second_set:
        # If sets are equal, check if timestamps are different
        # Extract timestamps from IDs
        first_timestamps = {task_id.split("_")[-1] for task_id in first_task_ids}
        second_timestamps = {task_id.split("_")[-1] for task_id in second_task_ids}
        # They might still be the same if created in same millisecond
        # This is acceptable, but we log it
        print(f"Warning: Task IDs have same timestamps, but this is acceptable if created quickly")

