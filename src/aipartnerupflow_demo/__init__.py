"""
aipartnerupflow-demo

Demo deployment of aipartnerupflow with rate limiting and pre-computed results.
"""

__version__ = "0.3.0"

# Import custom TaskModel extension to register it on package load
# This ensures CustomTaskModel is used by both API server and CLI tools
from aipartnerupflow_demo.extensions.custom_task_model_extension import *  # noqa: F401, F403

