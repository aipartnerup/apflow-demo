"""
Demo extensions module
"""

from aipartnerupflow_demo.extensions.rate_limiter import RateLimiter
from aipartnerupflow_demo.extensions.usage_tracker import UsageTracker

# Lazy imports for hooks to avoid import errors during pytest collection
# These are only imported when actually needed (in main.py)
__all__ = [
    "RateLimiter",
    "UsageTracker",
]

