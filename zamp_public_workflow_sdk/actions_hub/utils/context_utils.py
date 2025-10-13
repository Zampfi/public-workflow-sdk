"""
Simplified context utilities for ActionsHub - removes circular dependencies.
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


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


def get_log_mode_from_context():
    """
    Get the log mode from the context data.
    """
    from ..constants import LogMode
    from zamp_public_workflow_sdk.temporal import LOG_MODE_FIELD

    return get_variable_from_context(LOG_MODE_FIELD, LogMode.INFO)
