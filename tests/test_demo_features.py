"""
Tests for demo features
"""

import pytest
from aipartnerupflow_demo.extensions.rate_limiter import RateLimiter
from aipartnerupflow_demo.extensions.demo_results import DemoResultsCache
from aipartnerupflow_demo.config.settings import settings


def test_rate_limiter_initialization():
    """Test rate limiter initialization"""
    # Test that rate limiter can be instantiated
    assert RateLimiter is not None


def test_demo_results_cache():
    """Test demo results cache"""
    # Test that cache can be accessed
    assert DemoResultsCache is not None
    
    # Test listing demo tasks
    demo_tasks = DemoResultsCache.list_demo_tasks()
    assert isinstance(demo_tasks, list)


def test_settings():
    """Test settings loading"""
    assert settings is not None
    assert isinstance(settings.demo_mode, bool)
    assert isinstance(settings.rate_limit_enabled, bool)

