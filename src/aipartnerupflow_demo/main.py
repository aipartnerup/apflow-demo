"""
Main entry point for aipartnerupflow-demo
"""

import os
import sys
import uvicorn
from pathlib import Path
from aipartnerupflow_demo.api.server import create_demo_app
from aipartnerupflow_demo.config.settings import settings


def main():
    """Main entry point"""
    # Load environment variables from .env file if it exists
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    # Create demo application
    app = create_demo_app()
    
    # Get host and port from settings
    host = settings.aipartnerupflow_api_host
    port = settings.aipartnerupflow_api_port
    
    print(f"Starting aipartnerupflow-demo on {host}:{port}")
    print(f"Demo mode: {settings.demo_mode}")
    print(f"Rate limiting: {settings.rate_limit_enabled}")
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=1,  # Single worker for async app
        loop="asyncio",
        limit_concurrency=100,
        limit_max_requests=1000,
        access_log=True,
    )


if __name__ == "__main__":
    main()

