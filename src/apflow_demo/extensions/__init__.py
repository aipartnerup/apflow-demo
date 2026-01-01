"""
Demo extensions module
"""

# Import custom task model extension first to ensure it's registered
# This ensures both API server and CLI tools use the custom TaskModel
try:
    import apflow_demo.extensions.custom_task_model_extension  # noqa: F401
except ImportError:
    pass  # Extension may not be available in all environments

from apflow_demo.extensions.rate_limiter import RateLimiter
from apflow_demo.extensions.usage_tracker import UsageTracker

# Lazy imports for hooks to avoid import errors during pytest collection
# These are only imported when actually needed (in main.py)
__all__ = [
    "RateLimiter",
    "UsageTracker",
]

