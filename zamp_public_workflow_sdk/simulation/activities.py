"""
Activities for simulation support.

This module contains activities that are used to support simulation functionality,
such as making mocked operations visible in the Temporal UI.
"""

from typing import Any

import structlog
from temporalio import activity
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class MockedResultInput(BaseModel):
    """Input model for return_mocked_result activity."""

    node_id: str
    output: Any


@activity.defn(name="return_mocked_result")
async def return_mocked_result(input_data: MockedResultInput) -> Any:
    """
    Activity to return mocked results. This makes mocked operations visible in Temporal UI.

    Args:
        input_data: The input data containing node_id and output

    Returns:
        The mocked output value
    """

    logger.info("Returning mocked result", node_id=input_data.node_id)
    return input_data.output
