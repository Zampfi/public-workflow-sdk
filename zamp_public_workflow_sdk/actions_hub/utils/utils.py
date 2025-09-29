"""
Utility functions for ActionsHub - independent of Pantheon platform.
"""

import structlog
from zamp_public_workflow_sdk.temporal.data_converters.type_utils import (
    get_fqn as get_fqn_from_zamp,
)

logger = structlog.get_logger(__name__)


def get_fqn(cls):
    """
    Get the fully qualified name for a class using the zamp library.

    This is the default behavior for backward compatibility.
    For more flexible import path resolution (e.g., for test mocking),
    use get_import_path() instead.

    Args:
        cls: The class to get the FQN for

    Returns:
        str: The fully qualified name
    """
    return get_fqn_from_zamp(cls)
