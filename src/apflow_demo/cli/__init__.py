"""CLI package for apflow_demo"""
from __future__ import annotations
import sys
import runpy

def main() -> None:
    # Ensure CLI plugins are registered by importing them
    try:
        import apflow_demo.cli.users  # noqa: F401
    except Exception:
        pass
    try:
        import apflow_demo
    except Exception:
        pass
    try:
        from apflow.cli.main import app as _apflow_app
        _apflow_app()
    except Exception:
        runpy.run_module("apflow", run_name="__main__")
