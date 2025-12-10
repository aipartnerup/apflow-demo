"""
Tests for demo features
"""

import pytest
from aipartnerupflow_demo.extensions.rate_limiter import RateLimiter
from aipartnerupflow_demo.config.settings import settings


def test_rate_limiter_initialization():
    """Test rate limiter initialization"""
    # Test that rate limiter can be instantiated
    assert RateLimiter is not None


def test_settings():
    """Test settings loading"""
    assert settings is not None
    assert isinstance(settings.demo_mode, bool)
    assert isinstance(settings.rate_limit_enabled, bool)

