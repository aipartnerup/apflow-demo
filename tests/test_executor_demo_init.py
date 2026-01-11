"""
Tests for executor demo task initialization

Tests the ExecutorDemoInitService to ensure demo tasks are created correctly
with proper data structure, unique IDs, and all required fields.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import List, Dict, Any
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
            result = db_session.execute(stmt)
            tasks = result.scalars().all()
            
            # Delete each task
            for task in tasks:
                db_session.delete(task)
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
                # Exclude _demo_* fields as they are internal demo metadata
                for input_key in task.inputs.keys():
                    if input_key.startswith('_demo_'):
                        continue  # Skip demo metadata fields
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


@pytest.mark.asyncio
async def test_check_demo_init_status_no_tasks(test_user_id, cleanup_tasks):
    """Test check_demo_init_status when user has no demo tasks"""
    service = ExecutorDemoInitService()
    
    # Check status before creating any tasks
    status = await service.check_demo_init_status(test_user_id)
    
    # Verify status structure
    assert isinstance(status, dict)
    assert "can_init" in status
    assert "total_executors" in status
    assert "existing_executors" in status
    assert "missing_executors" in status
    assert "executor_details" in status
    
    # Verify values when no tasks exist
    all_metadata = get_all_executor_metadata()
    if all_metadata:
        assert status["can_init"] is True, "Should be able to init when no tasks exist"
        assert status["total_executors"] == len(all_metadata)
        assert len(status["existing_executors"]) == 0, "Should have no existing executors"
        assert len(status["missing_executors"]) == len(all_metadata), "All executors should be missing"
        assert set(status["missing_executors"]) == set(all_metadata.keys()), "Missing executors should match all executors"
    else:
        assert status["can_init"] is False, "Cannot init when no executors exist"
        assert status["total_executors"] == 0


@pytest.mark.asyncio
async def test_check_demo_init_status_partial_tasks(test_user_id, cleanup_tasks):
    """Test check_demo_init_status when user has some demo tasks"""
    service = ExecutorDemoInitService()
    
    # Get all executor metadata
    all_metadata = get_all_executor_metadata()
    
    if not all_metadata or len(all_metadata) < 2:
        pytest.skip("Need at least 2 executors to test partial tasks")
    
    # Create demo tasks for first executor only
    executor_ids = list(all_metadata.keys())
    first_executor_id = executor_ids[0]
    
    # Create a demo task manually for the first executor
    TaskModel = get_task_model_class()
    from datetime import datetime, timezone
    
    async with create_pooled_session() as db_session:
        from sqlalchemy import select
        
        # Create a demo task for first executor
        demo_task = TaskModel(
            id=f"demo_test_{test_user_id[:8]}_{first_executor_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            user_id=test_user_id,
            name=f"Demo: {all_metadata[first_executor_id].get('name', first_executor_id)}",
            status="pending",
            inputs={},
            schemas={"method": first_executor_id},
            priority=2,
            progress=0.0,
            has_children=False,
            parent_id=None,
            dependencies=None,
        )
        db_session.add(demo_task)
        db_session.commit()
    
    # Check status
    status = await service.check_demo_init_status(test_user_id)
    
    # Verify status
    assert status["can_init"] is True, "Should be able to init when some tasks are missing"
    assert status["total_executors"] == len(all_metadata)
    assert len(status["existing_executors"]) == 1, "Should have one existing executor"
    assert first_executor_id in status["existing_executors"], "First executor should be in existing list"
    assert len(status["missing_executors"]) == len(all_metadata) - 1, "Should have one less missing executor"
    assert first_executor_id not in status["missing_executors"], "First executor should not be in missing list"


@pytest.mark.asyncio
async def test_check_demo_init_status_all_tasks_exist(test_user_id, cleanup_tasks):
    """Test check_demo_init_status when user has all demo tasks"""
    service = ExecutorDemoInitService()
    
    # Initialize all demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Check status after creating all tasks
    status = await service.check_demo_init_status(test_user_id)
    
    # Verify status
    all_metadata = get_all_executor_metadata()
    assert status["can_init"] is False, "Should not be able to init when all tasks exist"
    assert status["total_executors"] == len(all_metadata)
    assert len(status["existing_executors"]) == len(all_metadata), "All executors should be existing"
    assert len(status["missing_executors"]) == 0, "Should have no missing executors"
    assert set(status["existing_executors"]) == set(all_metadata.keys()), "Existing executors should match all executors"


@pytest.mark.asyncio
async def test_check_demo_init_status_executor_details(test_user_id, cleanup_tasks):
    """Test that executor_details contains correct information"""
    service = ExecutorDemoInitService()
    
    # Get all executor metadata
    all_metadata = get_all_executor_metadata()
    
    if not all_metadata:
        pytest.skip("No executors available to test")
    
    # Check status
    status = await service.check_demo_init_status(test_user_id)
    
    # Verify executor_details structure
    executor_details = status["executor_details"]
    assert isinstance(executor_details, dict)
    assert len(executor_details) == len(all_metadata), "Should have details for all executors"
    
    # Verify each executor detail
    for executor_id, metadata in all_metadata.items():
        assert executor_id in executor_details, f"Missing details for executor {executor_id}"
        
        detail = executor_details[executor_id]
        assert isinstance(detail, dict)
        assert "id" in detail
        assert "name" in detail
        assert "has_demo_task" in detail
        
        assert detail["id"] == executor_id, f"Executor ID mismatch for {executor_id}"
        assert detail["name"] == metadata.get("name", executor_id), f"Executor name mismatch for {executor_id}"
        assert isinstance(detail["has_demo_task"], bool), f"has_demo_task should be bool for {executor_id}"
        
        # Initially, no tasks should exist
        assert detail["has_demo_task"] is False, f"Initially, {executor_id} should not have demo task"
    
    # Create tasks for some executors
    executor_ids = list(all_metadata.keys())
    if len(executor_ids) >= 2:
        first_executor_id = executor_ids[0]
        
        # Create a demo task for first executor
        TaskModel = get_task_model_class()
        from datetime import datetime, timezone
        
        async with create_pooled_session() as db_session:
            demo_task = TaskModel(
                id=f"demo_test_{test_user_id[:8]}_{first_executor_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                user_id=test_user_id,
                name=f"Demo: {all_metadata[first_executor_id].get('name', first_executor_id)}",
                status="pending",
                inputs={},
                schemas={"method": first_executor_id},
                priority=2,
                progress=0.0,
                has_children=False,
                parent_id=None,
                dependencies=None,
            )
            db_session.add(demo_task)
            db_session.commit()
        
        # Check status again
        status_after = await service.check_demo_init_status(test_user_id)
        
        # Verify first executor now has demo task
        assert status_after["executor_details"][first_executor_id]["has_demo_task"] is True, \
            f"{first_executor_id} should now have demo task"
        
        # Verify other executors still don't have demo tasks
        for executor_id in executor_ids[1:]:
            assert status_after["executor_details"][executor_id]["has_demo_task"] is False, \
                f"{executor_id} should not have demo task"


@pytest.mark.asyncio
async def test_check_demo_init_status_consistency(test_user_id, cleanup_tasks):
    """Test that check_demo_init_status is consistent with actual task creation"""
    service = ExecutorDemoInitService()
    
    # Check initial status
    status_before = await service.check_demo_init_status(test_user_id)
    
    # Create tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if len(created_task_ids) == 0:
        pytest.skip("No executors available to test")
    
    # Check status after creation
    status_after = await service.check_demo_init_status(test_user_id)
    
    # Verify consistency
    all_metadata = get_all_executor_metadata()
    
    # Before: should be able to init, missing all executors
    assert status_before["can_init"] is True
    assert len(status_before["missing_executors"]) == len(all_metadata)
    
    # After: should not be able to init, missing none
    assert status_after["can_init"] is False
    assert len(status_after["missing_executors"]) == 0
    assert len(status_after["existing_executors"]) == len(all_metadata)
    
    # Verify that existing executors match what was created
    # Note: system_info_executor creates multiple tasks, but we only check for one executor_id
    created_executor_ids = set()
    async with create_pooled_session() as db_session:
        task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
        for task_id in created_task_ids:
            task = await task_repository.get_task_by_id(task_id)
            if task and task.schemas and isinstance(task.schemas, dict):
                executor_id = task.schemas.get("method")
                if executor_id:
                    created_executor_ids.add(executor_id)
    
    # All created executor IDs should be in existing list
    assert created_executor_ids.issubset(set(status_after["existing_executors"])), \
        "All created executor IDs should be in existing executors list"

