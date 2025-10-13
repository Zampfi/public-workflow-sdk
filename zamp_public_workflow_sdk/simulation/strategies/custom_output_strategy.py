"""
Custom Output simulation strategy implementation.
"""

from typing import Any

import structlog

from zamp_public_workflow_sdk.simulation.models.simulation_response import (
    SimulationStrategyOutput,
)
from zamp_public_workflow_sdk.simulation.strategies.base_strategy import BaseStrategy

logger = structlog.get_logger(__name__)


class CustomOutputStrategyHandler(BaseStrategy):
    """
    Strategy that returns predefined custom outputs.
    """

    def __init__(self, output_value: Any):
        """
        Initialize with custom output value.

        Args:
            output_value: The custom output value to return
        """
        self.output_value = output_value

    async def execute(
        self,
        node_ids: list[str],
    ) -> SimulationStrategyOutput:
        """
        Execute Custom Output strategy.

        Args:
            node_ids: List of node execution IDs

        Returns:
            SimulationStrategyOutput with node_outputs for mocking
        """
        # Return the same custom output for all nodes
        node_outputs = {node_id: self.output_value for node_id in node_ids}
        return SimulationStrategyOutput(node_outputs=node_outputs)
