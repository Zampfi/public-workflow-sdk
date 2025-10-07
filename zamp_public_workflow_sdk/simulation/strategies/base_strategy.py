"""
Abstract base class for simulation strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

import structlog

from zamp_public_workflow_sdk.simulation.models.simulation_response import (
    SimulationStrategyOutput,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    WorkflowHistory,
)

logger = structlog.get_logger(__name__)


class BaseStrategy(ABC):
    """
    Abstract base class for all simulation strategies.
    Defines the contract that all concrete strategies must implement.
    """

    @abstractmethod
    async def execute(
        self,
        node_ids: List[str],
        temporal_history: Optional[WorkflowHistory] = None,
    ) -> SimulationStrategyOutput:
        """
        Execute the simulation strategy for multiple nodes.

        Args:
            node_ids: List of node execution IDs
            temporal_history: Optional workflow history (for strategies that need it)

        Returns:
            SimulationStrategyOutput containing:
            - node_outputs: Dictionary mapping node IDs to their mocked outputs, or empty dict if no mocking
        """
        pass
