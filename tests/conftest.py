"""
Pytest configuration and shared fixtures

This file ensures all tests share the same event loop, which is required
for SQLAlchemy async engine connection pool to work correctly.
"""

import asyncio
import logging
import pytest

# Suppress LiteLLM logging errors about missing apscheduler
logging.getLogger("litellm.litellm_core_utils.litellm_logging").setLevel(logging.CRITICAL)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create a session-scoped event loop for all tests.
    
    This ensures SQLAlchemy async engine connection pool binds to the same
    event loop across all tests, avoiding "Task got Future attached to a different loop" errors.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

