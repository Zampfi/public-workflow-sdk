"""
Custom Output simulation strategy implementation.
"""

import structlog
from typing import Any, List, Optional

from zamp_public_workflow_sdk.simulation.models.simulation_response import (
    SimulationStrategyOutput,
)
from zamp_public_workflow_sdk.simulation.strategies.base_strategy import BaseStrategy
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    WorkflowHistory,
)

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
        node_ids: List[str],
        temporal_history: Optional[WorkflowHistory] = None,
    ) -> SimulationStrategyOutput:
        """
        Execute Custom Output strategy.

        Args:
            node_ids: List of node execution IDs
            temporal_history: Optional workflow history (not used in this strategy)

        Returns:
            SimulationStrategyOutput with node_outputs for mocking
        """
        # Return the same custom output for all nodes
        node_outputs = {node_id: self.output_value for node_id in node_ids}
        return SimulationStrategyOutput(node_outputs=node_outputs)
