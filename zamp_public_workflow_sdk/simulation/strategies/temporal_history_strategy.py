"""
Temporal History simulation strategy implementation.
"""

import structlog

from zamp_public_workflow_sdk.simulation.helper import (
    MAIN_WORKFLOW_IDENTIFIER,
    extract_node_payload,
    fetch_temporal_history,
)
from zamp_public_workflow_sdk.simulation.models.simulation_response import (
    SimulationStrategyOutput,
)
from zamp_public_workflow_sdk.simulation.strategies.base_strategy import BaseStrategy
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    WorkflowHistory,
)

logger = structlog.get_logger(__name__)


class TemporalHistoryStrategyHandler(BaseStrategy):
    """
    Strategy that uses Temporal workflow history to mock node outputs.

    This strategy supports partial mocking of workflows:
    - Main workflow nodes: Mocked using reference workflow history
    - Child workflow nodes: Can be partially mocked by specifying individual
      activities/child workflows within the child workflow using nodeId notation
      (e.g., "ChildWorkflow#1.activity#1")

    The strategy automatically handles hierarchical workflows by:
    1. Grouping nodes by their parent workflow
    2. Fetching child workflow histories when needed
    3. Extracting outputs from the appropriate workflow history level
    """

    def __init__(self, reference_workflow_id: str, reference_workflow_run_id: str):
        """
        Initialize with reference workflow details.

        Args:
            reference_workflow_id: Reference workflow ID to fetch history from
            reference_workflow_run_id: Reference run ID to fetch history from
        """
        self.reference_workflow_id = reference_workflow_id
        self.reference_workflow_run_id = reference_workflow_run_id
        self.workflow_histories_map: dict[str, WorkflowHistory] = {}

    async def execute(
        self,
        node_ids: list[str],
    ) -> SimulationStrategyOutput:
        """
        Execute Temporal History strategy to extract node outputs.

        This method handles both main workflow and child workflow nodes. For child workflow
        nodes, it automatically fetches the child workflow history and extracts outputs.

        Args:
            node_ids: List of node execution IDs (supports hierarchical notation like
                     "ChildWorkflow#1.activity#1")

        Returns:
            SimulationStrategyOutput containing node outputs for mocking

        Raises:
            Exception: If temporal history cannot be fetched or node outputs cannot be extracted
        """
        try:
            temporal_history = await fetch_temporal_history(
                node_ids=node_ids,
                workflow_id=self.reference_workflow_id,
                run_id=self.reference_workflow_run_id,
            )
        except Exception as e:
            raise Exception(
                f"Failed to fetch temporal history for workflow_id={self.reference_workflow_id}, run_id={self.reference_workflow_run_id}"
            ) from e

        self.workflow_histories_map[MAIN_WORKFLOW_IDENTIFIER] = temporal_history

        node_id_to_payload_map = await extract_node_payload(
            node_ids=node_ids,
            workflow_histories_map=self.workflow_histories_map,
        )
        return SimulationStrategyOutput(node_id_to_payload_map=node_id_to_payload_map)
