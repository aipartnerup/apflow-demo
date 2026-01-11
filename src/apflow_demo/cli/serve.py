"""
CLI extension for running the demo API server
"""

import typer
from apflow.cli import CLIExtension, cli_register
from apflow_demo.main import start_server

@cli_register(name="serve", help="Start the apflow-demo API server", override=True)
def serve_app() -> None:
    """Start the apflow-demo API server (direct command)."""
    from apflow.logger import get_logger
    logger = get_logger(__name__)
    logger.warning("Start the apflow-demo API server")
    print("Start the apflow-demo API server...")
    start_server()