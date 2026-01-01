"""
Extension module to register custom TaskModel

This module automatically registers the custom TaskModel when imported.
It should be imported early in the application lifecycle to ensure
the custom TaskModel is used by both API server and CLI tools.
"""

from importlib import import_module
from apflow_demo.storage.models import CustomTaskModel
from apflow.core.utils.logger import get_logger

logger = get_logger(__name__)


def _register_custom_task_model():
    """Lazily import framework config and register CustomTaskModel.

    Importing `apflow.core.config` at module import time can
    trigger loading of the framework's SQLAlchemy models and create the
    default `TaskModel` mapping before our custom class is registered.
    Import `set_task_model_class` lazily to ensure registration happens
    before the framework config/module creates its mappings.
    """
    try:
        cfg = import_module("apflow.core.config")
        set_task_model_class = getattr(cfg, "set_task_model_class", None)
        if callable(set_task_model_class):
            set_task_model_class(CustomTaskModel)
            logger.info("Registered custom TaskModel with token_usage and instance_id fields")
        else:
            logger.warning("set_task_model_class not found in framework config")
    except Exception as e:
        logger.warning(f"Failed to register custom TaskModel: {e}")


# Perform registration when this module is imported, but using the lazy
# helper to avoid importing framework metadata too early.
_register_custom_task_model()

