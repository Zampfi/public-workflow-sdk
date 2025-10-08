"""
Temporal History simulation strategy implementation.
"""

from typing import Dict, List
import structlog
from typing import Any, Optional

from zamp_public_workflow_sdk.simulation.models.simulation_response import (
    SimulationStrategyOutput,
)
from zamp_public_workflow_sdk.simulation.strategies.base_strategy import BaseStrategy
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    WorkflowHistory,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.fetch_temporal_workflow_history import (
    FetchTemporalWorkflowHistoryInput,
    FetchTemporalWorkflowHistoryOutput,
)


logger = structlog.get_logger(__name__)


class TemporalHistoryStrategyHandler(BaseStrategy):
    """
    Strategy that uses Temporal workflow history to mock node outputs.
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

    async def execute(
        self,
        node_ids: List[str],
        temporal_history: Optional[WorkflowHistory] = None,
    ) -> SimulationStrategyOutput:
        """
        Execute Temporal History strategy.

        Args:
            node_ids: List of node execution IDs
            temporal_history: Optional workflow history (if already fetched)

        Returns:
            SimulationStrategyOutput with node_outputs for mocking when history is found
        """
        try:
            if temporal_history is None:
                temporal_history = await self._fetch_temporal_history(node_ids)

            if temporal_history is not None:
                output = await self._extract_node_output(temporal_history, node_ids)
                return SimulationStrategyOutput(node_outputs=output)

            return SimulationStrategyOutput()

        except Exception as e:
            logger.error(
                "TemporalHistoryStrategyHandler: Error executing strategy",
                node_ids=node_ids,
                error=str(e),
                error_type=type(e).__name__,
            )
            return SimulationStrategyOutput()

    async def _fetch_temporal_history(
        self, node_ids: List[str]
    ) -> Optional[WorkflowHistory]:
        """
        Fetch temporal workflow history for reference workflow.

        Returns:
            WorkflowHistory object or None if fetch fails
        """
        from zamp_public_workflow_sdk.actions_hub import ActionsHub

        try:
            workflow_history = await ActionsHub.execute_child_workflow(
                "FetchTemporalWorkflowHistoryWorkflow",
                FetchTemporalWorkflowHistoryInput(
                    workflow_id=self.reference_workflow_id,
                    run_id=self.reference_workflow_run_id,
                    node_ids=node_ids,
                ),
                result_type=FetchTemporalWorkflowHistoryOutput,
            )
            return workflow_history

        except Exception as e:
            logger.error(
                "Failed to fetch temporal history",
                error=str(e),
                error_type=type(e).__name__,
                reference_workflow_id=self.reference_workflow_id,
                reference_workflow_run_id=self.reference_workflow_run_id,
            )
            return None

    async def _extract_node_output(
        self, temporal_history: WorkflowHistory, node_ids: List[str]
    ) -> Dict[str, Optional[Any]]:
        """
        Extract output for specific nodes from temporal history.

        Args:
            temporal_history: The workflow history object
            node_ids: List of node execution IDs to extract output for

        Returns:
            Dictionary mapping node IDs to their outputs or None if not found
        """
        try:
            logger.info(
                "Extracting node output",
                node_ids=node_ids,
            )
            nodes_data = {}
            for node_id in node_ids:
                output = temporal_history.get_node_output(node_id)
                nodes_data[node_id] = output
            return nodes_data

        except Exception as e:
            logger.error(
                "Error extracting node output",
                error=str(e),
                error_type=type(e).__name__,
                node_ids=node_ids,
            )
            return {}
