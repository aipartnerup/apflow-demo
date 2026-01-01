"""
Task tree detection utilities

Detects whether tasks or task trees are LLM-consuming.
"""

from typing import Dict, Any, Optional, List
from apflow.core.types import TaskTreeNode
from apflow.core.storage.sqlalchemy.models import TaskModel


# LLM-consuming executor IDs
LLM_EXECUTOR_IDS = {
    "crewai_executor",
    "generate_executor",
    "openai_executor",
    "anthropic_executor",
    "llm_executor",
}

# LLM-consuming executor types
LLM_EXECUTOR_TYPES = {
    "crewai",
    "generate",
    "openai",
    "anthropic",
    "llm",
    "agent",
}


def is_llm_consuming_task_schema(schemas: Optional[Dict[str, Any]]) -> bool:
    """
    Check if task schemas indicate LLM-consuming executor
    
    Args:
        schemas: Task schemas dictionary
        
    Returns:
        True if schemas indicate LLM-consuming executor
    """
    if not schemas:
        return False
    
    # Check method in schemas (can be executor id)
    method = schemas.get("method", "").lower()
    if method in LLM_EXECUTOR_IDS:
        return True
    
    # Check type in schemas
    task_type = schemas.get("type", "").lower()
    if task_type in LLM_EXECUTOR_TYPES:
        return True
    
    # Check if method contains LLM-related keywords
    if method and any(keyword in method for keyword in ["llm", "openai", "anthropic", "crewai", "generate"]):
        return True
    
    return False


def is_llm_consuming_task(task: TaskModel) -> bool:
    """
    Check if a single task requires LLM API calls
    
    Args:
        task: TaskModel instance
        
    Returns:
        True if task is LLM-consuming
    """
    schemas = task.schemas or {}
    params = task.params or {}
    
    # Check executor_id in params
    executor_id = params.get("executor_id")
    if executor_id and executor_id.lower() in LLM_EXECUTOR_IDS:
        return True
    
    # Check method in schemas (can be executor id)
    method = schemas.get("method", "").lower()
    if method in LLM_EXECUTOR_IDS:
        return True
    
    # Check type in schemas
    task_type = schemas.get("type", "").lower()
    if task_type in LLM_EXECUTOR_TYPES:
        return True
    
    # Check if method contains LLM-related keywords
    if method and any(keyword in method for keyword in ["llm", "openai", "anthropic", "crewai", "generate"]):
        return True
    
    # Check params for LLM-related configuration
    if params:
        params_str = str(params).lower()
        if any(keyword in params_str for keyword in ["llm", "openai", "anthropic", "crewai", "model"]):
            # Check if it's actually LLM-related (not just a string containing the word)
            works = params.get("works", {})
            if works:
                # CrewAI works configuration indicates LLM usage
                return True
    
    return False


def is_llm_consuming_task_tree(root_task: TaskModel) -> bool:
    """
    Check if a task tree contains any LLM-consuming tasks
    
    Args:
        root_task: Root TaskModel instance
        
    Returns:
        True if task tree contains any LLM-consuming tasks
    """
    # Check root task
    if is_llm_consuming_task(root_task):
        return True
    
    # Note: For full tree traversal, we would need TaskRepository
    # This function checks only the root task for now
    # Full tree traversal should be done with TaskTreeNode or TaskRepository
    return False


def is_llm_consuming_task_tree_node(task_tree_node: TaskTreeNode) -> bool:
    """
    Check if a task tree (TaskTreeNode) contains any LLM-consuming tasks
    
    Args:
        task_tree_node: Root TaskTreeNode instance
        
    Returns:
        True if task tree contains any LLM-consuming tasks
    """
    # Check root task
    if is_llm_consuming_task(task_tree_node.task):
        return True
    
    # Recursively check children
    for child_node in task_tree_node.children:
        if is_llm_consuming_task_tree_node(child_node):
            return True
    
    return False


def detect_task_tree_from_tasks_array(tasks: List[Dict[str, Any]]) -> bool:
    """
    Detect if a tasks array contains LLM-consuming tasks
    
    Args:
        tasks: List of task dictionaries
        
    Returns:
        True if any task is LLM-consuming
    """
    for task_dict in tasks:
        schemas = task_dict.get("schemas", {})
        params = task_dict.get("params", {})
        
        # Check executor_id
        executor_id = params.get("executor_id", "").lower()
        if executor_id in LLM_EXECUTOR_IDS:
            return True
        
        # Check method
        method = schemas.get("method", "").lower()
        if method in LLM_EXECUTOR_IDS:
            return True
        
        # Check type
        task_type = schemas.get("type", "").lower()
        if task_type in LLM_EXECUTOR_TYPES:
            return True
        
        # Check for LLM keywords
        if method and any(keyword in method for keyword in ["llm", "openai", "anthropic", "crewai", "generate"]):
            return True
        
        # Check params for works configuration (CrewAI)
        if params.get("works"):
            return True
    
    return False

