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
        from apflow_demo.main import start_server
        
        # Add serve command to start the demo server
        @_apflow_app.command("serve", help="Start the apflow-demo API server")
        def serve() -> None:
            """Start the apflow-demo API server"""
            start_server()
        
        # CLI extensions registered via @cli_register decorator are automatically
        # loaded by apflow's LazyGroup when apflow_demo.cli.users is imported above
        _apflow_app()
    except Exception:
        runpy.run_module("apflow", run_name="__main__")
