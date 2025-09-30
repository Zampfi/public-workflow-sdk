"""
Simplified context utilities for ActionsHub - removes circular dependencies.
"""

import structlog
from typing import Any


def get_variable_from_context(variable_name: str, default_value: Any = None) -> Any:
    """
    Get a variable from the context data.
    Args:
        variable_name: The name of the variable to get
        default_value: The default value to return if the variable is not found
    Returns:
        The value of the variable
    """
    context_vars = structlog.contextvars.get_contextvars()
    return context_vars.get(variable_name, default_value)


def get_execution_mode_from_context():
    """
    Get the execution mode from the context data.
    """
    from ..constants import ExecutionMode

    return get_variable_from_context("execution_mode", ExecutionMode.TEMPORAL)
