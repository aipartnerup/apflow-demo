"""CLI wrapper that imports the demo package before delegating to the
original `apflow` console entrypoint. This ensures the demo package
is imported in the same process so `CustomTaskModel` is registered
before the apflow CLI runs.

Install the package editable and run `apflow-with-demo ...` instead
of `apflow ...` when you want the demo extensions loaded.
"""
from __future__ import annotations

import sys
import runpy


def main() -> None:
    """Import demo package (registers CustomTaskModel) then run apflow.

    This function is intended to be registered as a console script entry
    point in `pyproject.toml` so it receives the original CLI args in
    `sys.argv`.
    """
    try:
        # Import package to trigger registration side-effects
        import aipartnerupflow_demo  # noqa: F401
    except Exception:
        # If import fails, continue and let apflow error as usual
        pass

    # Delegate to the installed `apflow` console script implementation.
    # The global `apflow` entrypoint calls `aipartnerupflow.cli.main.app()`;
    # import and call the same callable so args are preserved in this
    # process (and the demo package remains imported).
    try:
        from aipartnerupflow.cli.main import app as _apflow_app
        _apflow_app()
    except Exception:
        # Fall back to runpy if the above import path changes in future
        runpy.run_module("apflow", run_name="__main__")


if __name__ == "__main__":
    main()
