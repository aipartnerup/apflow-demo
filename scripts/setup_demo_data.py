#!/usr/bin/env python3
"""
Script to setup demo data

Initializes demo tasks from aipartnerupflow examples.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aipartnerupflow.examples.init import init_examples_data


async def main():
    """Main function"""
    print("Setting up demo data...")
    
    # Initialize example tasks from aipartnerupflow
    print("Initializing example tasks...")
    count = await init_examples_data(force=False)
    print(f"Initialized {count} example tasks")
    
    print("\nDemo data setup complete!")
    print("Note: Demo mode uses aipartnerupflow v0.6.0's built-in use_demo parameter")


if __name__ == "__main__":
    asyncio.run(main())

