"""
Test execution of demo tasks.

This test verifies that demo tasks created by ExecutorDemoInitService
can be executed by their corresponding executors.
"""

import pytest
import pytest_asyncio
import asyncio
import inspect
from typing import List, Dict, Any
from apflow_demo.services.executor_demo_init import ExecutorDemoInitService
from apflow.core.storage import create_pooled_session
from apflow.core.storage.sqlalchemy.task_repository import TaskRepository
from apflow.core.config import get_task_model_class
from apflow.core.extensions.registry import get_registry
from apflow.logger import get_logger

# Import executors to ensure they are registered in tests
# Production code uses auto_initialize_extensions=True in create_runnable_app()
# which automatically loads all extensions via ExtensionScanner
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
    import apflow.extensions.scrape.scrape_executor
except ImportError as e:
    print(f"Warning: Failed to import some executors: {e}")

logger = get_logger(__name__)

# Executors that require external services or special environment
SKIP_EXECUTORS = {
    'docker_executor': 'Requires Docker daemon running',
    'ssh_executor': 'Requires SSH server (could test with localhost + temp key)',
    'mcp_executor': 'Requires MCP server (no public servers available)',
    'grpc_executor': 'Requires gRPC server (no reliable public API)',
    'apflow_api_executor': 'Requires running apflow instance',
    'generate_executor': 'Requires OPENAI_API_KEY environment variable',
    'command_executor': 'Disabled by default for security (requires APFLOW_STDIO_ALLOW_COMMAND=1)',
}


@pytest.fixture
def test_user_id():
    """Generate a test user ID"""
    return "test_user_executor_execution_12345"


@pytest_asyncio.fixture
async def db_session():
    """Get database session"""
    async with create_pooled_session() as session:
        yield session


@pytest_asyncio.fixture
async def cleanup_tasks(test_user_id):
    """Cleanup fixture to remove test tasks after test"""
    yield
    # Cleanup: remove all test tasks
    try:
        from sqlalchemy import select
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
    except Exception:
        pass


@pytest.mark.asyncio
async def test_execute_all_demo_tasks(test_user_id, cleanup_tasks):
    """
    Test that all initialized demo tasks can be successfully executed.
    
    This test:
    1. Initializes demo tasks for all executors.
    2. Retrieves them from the DB.
    3. Instantiates the appropriate executor for each task.
    4. Runs executor.execute(task).
    5. Verifies the result.
    
    Note: Some executors require external services (Docker, SSH, etc.) and are skipped.
    """
    service = ExecutorDemoInitService()
    
    # 1. Initialize demo tasks
    created_task_ids = await service.init_all_executor_demo_tasks_for_user(test_user_id)
    
    if not created_task_ids:
        pytest.skip("No executors/tasks available to test")
        
    print(f"\nCreated {len(created_task_ids)} tasks for execution test.")
    
    # 2. Retrieve tasks
    async with create_pooled_session() as db_session:
        task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
        
        failures = []
        successes = []
        skipped = []
        
        for task_id in created_task_ids:
            task = await task_repository.get_task_by_id(task_id)
            if not task:
                failures.append(f"Task {task_id} not found in DB")
                continue
                
            executor_id = task.schemas.get('method')
            task_name = task.name
            print(f"\nTesting execution for: {task_name} (Executor: {executor_id})")
            
            # Skip executors that require external services
            if executor_id in SKIP_EXECUTORS:
                skip_reason = SKIP_EXECUTORS[executor_id]
                print(f"  Skipped: {skip_reason}")
                skipped.append(f"{executor_id}: {skip_reason}")
                continue
            
            try:
                # 3. Get Executor
                registry = get_registry()
                executor = registry.get_executor(executor_id)
                
                if not executor:
                    failures.append(f"Executor '{executor_id}' not found in registry")
                    continue
                    
                # Check if it's a class or instance
                if inspect.isclass(executor):
                    try:
                        executor = executor()
                    except Exception as e:
                        failures.append(f"Failed to instantiate executor class {executor_id}: {e}")
                        continue

                # 4. Execute
                if not hasattr(executor, 'execute'):
                    failures.append(f"Executor {executor_id} has no 'execute' method")
                    continue
                
                print(f"  Executing {executor_id}...")
                print(f"  Task Inputs: {task.inputs}")
                
                try:
                    # Executors expect inputs dict, not TaskModel object
                    inputs = task.inputs or {}
                    
                    # Pass inputs directly to executor
                    if asyncio.iscoroutinefunction(executor.execute):
                        result = await executor.execute(inputs)
                    else:
                        result = executor.execute(inputs)
                    
                    print(f"  Result: {str(result)[:100]}...")
                    
                    # Check if result indicates failure
                    if isinstance(result, dict):
                        if result.get('status') == 'failed' or result.get('success') == False:
                            error_msg = result.get('error', 'Unknown error')
                            # Some failures are expected (e.g., command_executor disabled by default)
                            if 'disabled' in str(error_msg).lower() or 'security' in str(error_msg).lower():
                                skipped.append(f"{executor_id}: {error_msg[:50]}...")
                            else:
                                failures.append(f"Execution returned failure for {executor_id}: {error_msg[:100]}")
                        else:
                            successes.append(f"{executor_id}: Success")
                    else:
                        successes.append(f"{executor_id}: Success")
                    
                except Exception as exec_err:
                    failures.append(f"Execution failed for {executor_id} ({task_name}): {exec_err}")
                    
            except Exception as e:
                failures.append(f"Unexpected error processing {task_id}: {e}")

    # Report results
    print("\n\n=== Execution Test Summary ===")
    print(f"Total Tasks: {len(created_task_ids)}")
    print(f"Successes: {len(successes)}")
    print(f"Skipped (expected): {len(skipped)}")
    print(f"Failures: {len(failures)}")
    
    if skipped:
        print("\n=== Skipped (Expected) ===")
        for s in skipped:
            print(f"- {s}")
    
    if failures:
        print("\n=== Failures Details ===")
        for f in failures:
            print(f"- {f}")
        
        # Fail the test if there are any unexpected failures
        pytest.fail(f"Failed to execute {len(failures)} tasks. See stdout for details.")
    else:
        print("\nAll executable demo tasks completed successfully!")
