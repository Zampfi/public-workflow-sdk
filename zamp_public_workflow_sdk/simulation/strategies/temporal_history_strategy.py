"""
Temporal History simulation strategy implementation.
"""

from typing import Any

import structlog


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

# Constants
MAIN_WORKFLOW_IDENTIFIER = "main_workflow"  # Identifier for top-level workflow nodes


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

    async def execute(
        self,
        node_ids: list[str],
        temporal_history: WorkflowHistory | None = None,
    ) -> SimulationStrategyOutput:
        """
        Execute Temporal History strategy to extract node outputs.

        This method handles both main workflow and child workflow nodes. For child workflow
        nodes, it automatically fetches the child workflow history and extracts outputs.

        Args:
            node_ids: List of node execution IDs (supports hierarchical notation like
                     "ChildWorkflow#1.activity#1")
            temporal_history: Optional workflow history (fetches from Temporal if not provided)

        Returns:
            SimulationStrategyOutput containing node outputs for mocking, or empty output on failure
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
        self, node_ids: list[str], workflow_id: str | None = None, run_id: str | None = None
    ) -> WorkflowHistory | None:
        """
        Fetch temporal workflow history for a workflow (main or child).

        This method fetches the workflow history from Temporal, which includes all events
        for the specified workflow execution. If workflow_id and run_id are not provided,
        it defaults to the reference workflow.

        Args:
            node_ids: List of node execution IDs to filter history for
            workflow_id: Optional workflow ID to fetch (defaults to reference_workflow_id)
            run_id: Optional run ID to fetch (defaults to reference_workflow_run_id)

        Returns:
            WorkflowHistory object if successful, None if fetch fails
        """
        from zamp_public_workflow_sdk.actions_hub import ActionsHub

        try:
            target_workflow_id = workflow_id or self.reference_workflow_id
            target_run_id = run_id or self.reference_workflow_run_id
            workflow_history = await ActionsHub.execute_child_workflow(
                "FetchTemporalWorkflowHistoryWorkflow",
                FetchTemporalWorkflowHistoryInput(
                    workflow_id=target_workflow_id,
                    run_id=target_run_id,
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
                target_workflow_id=target_workflow_id,
                target_run_id=target_run_id,
                reference_workflow_id=self.reference_workflow_id,
                reference_workflow_run_id=self.reference_workflow_run_id,
            )
            return None

    async def _extract_node_output(
        self, temporal_history: WorkflowHistory, node_ids: list[str]
    ) -> dict[str, Any | None]:
        """
        Extract output for specific nodes from temporal history.

        This method handles both main workflow nodes and child workflow nodes.
        For child workflow nodes, it recursively fetches their history and extracts outputs.

        Args:
            temporal_history: The workflow history object (main workflow or parent workflow)
            node_ids: List of node execution IDs to extract output for

        Returns:
            Dictionary mapping node IDs to their outputs (None if not found)
        """
        try:
            logger.info("Extracting node outputs", node_ids=node_ids)

            # Group nodes by their immediate parent workflow
            nodes_by_parent = self._group_nodes_by_parent_workflow(node_ids)
            all_node_outputs = {}

            for parent_workflow_id, nodes_in_workflow in nodes_by_parent.items():
                if parent_workflow_id == MAIN_WORKFLOW_IDENTIFIER:
                    # Main workflow nodes - extract directly from current history
                    main_workflow_outputs = self._extract_main_workflow_node_outputs(
                        temporal_history, nodes_in_workflow
                    )
                    all_node_outputs.update(main_workflow_outputs)
                else:
                    # Child workflow nodes - need to fetch child workflow history
                    child_workflow_outputs = await self._extract_child_workflow_node_outputs(
                        temporal_history,
                        parent_workflow_id,
                        nodes_in_workflow,
                    )
                    all_node_outputs.update(child_workflow_outputs)

            return all_node_outputs

        except Exception as e:
            logger.error(
                "Error extracting node outputs",
                error=str(e),
                error_type=type(e).__name__,
                node_ids=node_ids,
            )
            # Return empty dict on error
            return {node_id: None for node_id in node_ids}

    def _extract_main_workflow_node_outputs(
        self, temporal_history: WorkflowHistory, node_ids: list[str]
    ) -> dict[str, Any | None]:
        """
        Extract outputs for nodes that belong to the main workflow.

        Args:
            temporal_history: The main workflow history object
            node_ids: List of node IDs in the main workflow

        Returns:
            Dictionary mapping node IDs to their outputs
        """
        node_outputs = {}
        for node_id in node_ids:
            output = temporal_history.get_node_output(node_id)
            node_outputs[node_id] = output
        return node_outputs

    async def _extract_child_workflow_node_outputs(
        self,
        parent_history: WorkflowHistory,
        child_workflow_id: str,
        node_ids: list[str],
    ) -> dict[str, Any | None]:
        """
        Extract outputs for nodes that belong to a child workflow.

        This method:
        1. Gets child workflow's workflow_id and run_id from parent's history
        2. Fetches the child workflow's history
        3. Extracts node outputs from child workflow history

        Args:
            parent_history: The parent workflow history object
            child_workflow_id: The child workflow identifier (e.g., "ChildWorkflow#1")
            node_ids: List of node IDs in the child workflow

        Returns:
            Dictionary mapping node IDs to their outputs (None if not found)
        """
        # Get child workflow's workflow_id and run_id from parent's history
        workflow_id_run_id = parent_history.get_child_workflow_workflow_id_run_id(child_workflow_id)

        if not workflow_id_run_id:
            logger.warning(
                "Child workflow workflow_id and run_id not found in parent history",
                child_workflow_id=child_workflow_id,
                parent_workflow_id=parent_history.workflow_id,
            )
            return {node_id: None for node_id in node_ids}

        workflow_id, run_id = workflow_id_run_id

        # Fetch child workflow history
        child_history = await self._fetch_temporal_history(
            node_ids=node_ids,
            workflow_id=workflow_id,
            run_id=run_id,
        )

        if not child_history:
            logger.warning(
                "Failed to fetch child workflow history",
                child_workflow_id=child_workflow_id,
                workflow_id=workflow_id,
                run_id=run_id,
            )
            return {node_id: None for node_id in node_ids}

        # Extract node data from child workflow history
        child_nodes_data = child_history.get_nodes_data()

        # Map node IDs to their outputs
        node_outputs = {}
        for node_id in node_ids:
            if node_id in child_nodes_data:
                node_outputs[node_id] = child_nodes_data[node_id].output_payload
            else:
                logger.warning(
                    "Node not found in child workflow history",
                    node_id=node_id,
                    child_workflow_id=child_workflow_id,
                )
                node_outputs[node_id] = None

        return node_outputs

    def _group_nodes_by_parent_workflow(self, node_ids: list[str]) -> dict[str, list[str]]:
        """
        Group node IDs by their immediate parent workflow.

        Node IDs follow a hierarchical dot notation where each node belongs to a parent workflow:
        - Main workflow nodes: 'activity#1' -> parent = MAIN_WORKFLOW_IDENTIFIER
        - Direct child workflow nodes: 'ChildWorkflow#1.activity#1' -> parent = 'ChildWorkflow#1'
        - Nested child workflow nodes: 'Parent#1.Child#1.activity#1' -> parent = 'Child#1'

        Args:
            node_ids: List of node execution IDs to group

        Returns:
            Dictionary mapping parent workflow identifier to list of its child node IDs
        """
        nodes_by_parent = {}

        # Sort by nesting depth (dot count) to process shallower nodes first
        sorted_node_ids = sorted(node_ids, key=lambda node_id: node_id.count("."))

        for node_id in sorted_node_ids:
            # Split node ID to identify parent workflow
            # Examples:
            #   'activity#1' -> ['activity#1']
            #   'Child#1.activity#1' -> ['Child#1', 'activity#1']
            #   'Parent#1.Child#1.activity#1' -> ['Parent#1', 'Child#1', 'activity#1']
            path_parts = node_id.split(".")

            if len(path_parts) == 1:
                # Top-level node in main workflow
                parent_workflow_id = MAIN_WORKFLOW_IDENTIFIER
            else:
                # Node in child workflow - immediate parent is the second-to-last element
                parent_workflow_id = path_parts[-2]

            if parent_workflow_id not in nodes_by_parent:
                nodes_by_parent[parent_workflow_id] = []

            nodes_by_parent[parent_workflow_id].append(node_id)

        return nodes_by_parent
