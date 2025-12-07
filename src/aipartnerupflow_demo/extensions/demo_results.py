"""
Demo results cache extension

Provides pre-computed results for demo tasks to avoid LLM API costs.
"""

import json
import os
from pathlib import Path
from typing import Optional, Any, Dict
from aipartnerupflow_demo.config.settings import settings


class DemoResultsCache:
    """Cache for pre-computed demo task results"""
    
    _cache: Dict[str, Any] = {}
    _cache_loaded = False
    
    @classmethod
    def _get_demo_dir(cls) -> Path:
        """Get demo directory path"""
        # Try to find demo directory relative to package
        package_dir = Path(__file__).parent.parent.parent.parent
        demo_dir = package_dir / "demo" / "precomputed_results"
        return demo_dir
    
    @classmethod
    def _load_cache(cls) -> None:
        """Load pre-computed results from files"""
        if cls._cache_loaded:
            return
        
        demo_dir = cls._get_demo_dir()
        if not demo_dir.exists():
            print(f"Warning: Demo directory not found: {demo_dir}")
            cls._cache_loaded = True
            return
        
        # Load all JSON files in precomputed_results directory
        for json_file in demo_dir.glob("*.json"):
            try:
                task_id = json_file.stem
                with open(json_file, "r", encoding="utf-8") as f:
                    cls._cache[task_id] = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load demo result from {json_file}: {e}")
        
        cls._cache_loaded = True
        print(f"Loaded {len(cls._cache)} pre-computed demo results")
    
    @classmethod
    def get_result(cls, task_id: str) -> Optional[Any]:
        """
        Get pre-computed result for a task
        
        Args:
            task_id: Task ID
            
        Returns:
            Pre-computed result or None if not found
        """
        if not settings.demo_mode:
            return None
        
        cls._load_cache()
        return cls._cache.get(task_id)
    
    @classmethod
    def has_result(cls, task_id: str) -> bool:
        """
        Check if pre-computed result exists for a task
        
        Args:
            task_id: Task ID
            
        Returns:
            True if result exists
        """
        if not settings.demo_mode:
            return False
        
        cls._load_cache()
        return task_id in cls._cache
    
    @classmethod
    def is_demo_task(cls, task_id: str) -> bool:
        """
        Check if task is a demo task (has pre-computed result)
        
        Args:
            task_id: Task ID
            
        Returns:
            True if task is a demo task
        """
        return cls.has_result(task_id)
    
    @classmethod
    def list_demo_tasks(cls) -> list[str]:
        """
        List all available demo task IDs
        
        Returns:
            List of task IDs
        """
        cls._load_cache()
        return list(cls._cache.keys())
    
    @classmethod
    def save_result(cls, task_id: str, result: Any) -> None:
        """
        Save a pre-computed result (for script use)
        
        Args:
            task_id: Task ID
            result: Result data
        """
        demo_dir = cls._get_demo_dir()
        demo_dir.mkdir(parents=True, exist_ok=True)
        
        json_file = demo_dir / f"{task_id}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Update cache
        cls._cache[task_id] = result

