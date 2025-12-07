#!/usr/bin/env python3
"""
Script to setup demo data

Initializes demo tasks and pre-computed results.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aipartnerupflow.examples.init import init_examples_data
from aipartnerupflow_demo.extensions.demo_results import DemoResultsCache


async def main():
    """Main function"""
    print("Setting up demo data...")
    
    # Initialize example tasks from aipartnerupflow
    print("Initializing example tasks...")
    count = await init_examples_data(force=False)
    print(f"Initialized {count} example tasks")
    
    # Load demo results cache
    print("Loading demo results cache...")
    demo_tasks = DemoResultsCache.list_demo_tasks()
    print(f"Found {len(demo_tasks)} pre-computed demo results")
    
    print("\nDemo data setup complete!")


if __name__ == "__main__":
    asyncio.run(main())

