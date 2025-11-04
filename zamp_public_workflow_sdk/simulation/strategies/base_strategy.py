"""
Abstract base class for simulation strategies.
"""

from abc import ABC, abstractmethod

import structlog

from zamp_public_workflow_sdk.simulation.models.simulation_response import (
    SimulationStrategyOutput,
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
        node_ids: list[str],
    ) -> SimulationStrategyOutput:
        """
        Execute the simulation strategy for multiple nodes.

        Args:
            node_ids: List of node execution IDs

        Returns:
            SimulationStrategyOutput containing:
            - node_id_to_payload_map: Dictionary mapping node IDs to their mocked outputs, or empty dict if no mocking
        """
        pass
