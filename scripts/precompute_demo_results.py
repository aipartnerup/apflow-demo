#!/usr/bin/env python3
"""
Script to pre-compute demo task results

This script executes demo tasks and saves their results for use in demo mode.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aipartnerupflow import TaskManager, create_session
from aipartnerupflow_demo.extensions.demo_results import DemoResultsCache


async def precompute_task_result(task_id: str, task_definition: dict) -> dict:
    """
    Pre-compute result for a demo task
    
    Args:
        task_id: Task ID
        task_definition: Task definition
        
    Returns:
        Task result
    """
    print(f"Pre-computing result for task: {task_id}")
    
    # Create database session
    db = create_session()
    task_manager = TaskManager(db)
    
    try:
        # Create task
        task = await task_manager.task_repository.create_task(
            name=task_definition.get("name", task_id),
            user_id="demo_user",
            inputs=task_definition.get("inputs", {}),
            schemas=task_definition.get("schemas", {}),
            parent_id=task_definition.get("parent_id"),
            priority=task_definition.get("priority", 1),
            dependencies=task_definition.get("dependencies", []),
        )
        
        # Execute task
        from aipartnerupflow.core.task_tree import TaskTreeNode
        task_tree = TaskTreeNode(task)
        await task_manager.distribute_task_tree(task_tree)
        
        # Get result
        result_task = await task_manager.task_repository.get_task_by_id(task.id)
        
        # Build result dictionary
        result = {
            "id": result_task.id,
            "status": result_task.status,
            "result": result_task.result,
            "progress": result_task.progress,
            "started_at": result_task.started_at.isoformat() if result_task.started_at else None,
            "completed_at": result_task.completed_at.isoformat() if result_task.completed_at else None,
        }
        
        print(f"✓ Task {task_id} completed: {result_task.status}")
        return result
        
    except Exception as e:
        print(f"✗ Error pre-computing task {task_id}: {e}")
        raise


async def main():
    """Main function"""
    # Load demo tasks
    demo_tasks_file = Path(__file__).parent.parent / "demo" / "demo_tasks.json"
    if not demo_tasks_file.exists():
        print(f"Error: Demo tasks file not found: {demo_tasks_file}")
        return
    
    with open(demo_tasks_file, "r", encoding="utf-8") as f:
        demo_data = json.load(f)
    
    demo_tasks = demo_data.get("demo_tasks", [])
    
    print(f"Found {len(demo_tasks)} demo tasks to pre-compute")
    
    # Pre-compute results for each task
    for task_info in demo_tasks:
        task_id = task_info["id"]
        
        # Check if result already exists
        if DemoResultsCache.has_result(task_id):
            print(f"Task {task_id} already has pre-computed result, skipping...")
            continue
        
        # For now, we'll create a placeholder result
        # In a real scenario, you would execute the task with LLM API key
        print(f"Note: Task {task_id} requires manual execution with LLM API key")
        print(f"Please execute this task manually and save the result")
        
        # Create placeholder result structure
        placeholder_result = {
            "id": task_id,
            "status": "completed",
            "result": {
                "message": "This is a pre-computed demo result",
                "task_id": task_id,
                "note": "Replace this with actual task execution result",
            },
            "progress": 1.0,
            "started_at": None,
            "completed_at": None,
        }
        
        # Save placeholder (user should replace with real result)
        DemoResultsCache.save_result(task_id, placeholder_result)
        print(f"✓ Saved placeholder result for {task_id}")
        print(f"  Please replace with actual result from task execution")
    
    print("\nPre-computation complete!")
    print("Note: Replace placeholder results with actual task execution results")


if __name__ == "__main__":
    asyncio.run(main())

