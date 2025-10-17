"""
Activities for simulation support.

This module contains activities that are used to support simulation functionality,
such as making mocked operations visible in the Temporal UI.
"""

from typing import Any

import structlog
from temporalio import activity

logger = structlog.get_logger(__name__)


@activity.defn(name="return_mocked_result")
async def return_mocked_result(node_id: str, output: Any) -> Any:
    """
    Activity to return mocked results. This makes mocked operations visible in Temporal UI.

    Args:
        node_id: The node_id identifying the mocked operation
        output: The mocked output to return

    Returns:
        The mocked output value
    """

    logger.info("Returning mocked result", node_id=node_id)
    return output
