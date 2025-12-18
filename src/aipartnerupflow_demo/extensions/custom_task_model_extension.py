"""
Extension module to register custom TaskModel

This module automatically registers the custom TaskModel when imported.
It should be imported early in the application lifecycle to ensure
the custom TaskModel is used by both API server and CLI tools.
"""

from aipartnerupflow.core.config import set_task_model_class
from aipartnerupflow_demo.storage.models import CustomTaskModel
from aipartnerupflow.core.utils.logger import get_logger

logger = get_logger(__name__)

# Register custom TaskModel
# This will be called when the module is imported
try:
    set_task_model_class(CustomTaskModel)
    logger.info("Registered custom TaskModel with token_usage and instance_id fields")
except Exception as e:
    logger.warning(f"Failed to register custom TaskModel: {e}")
    # Fall back to default TaskModel if registration fails

