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
                simulation_strategy_output = SimulationStrategyOutput(node_outputs=output)
                return simulation_strategy_output

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

            cached_histories = {}
            workflow_nodes_needed = self._collect_nodes_per_workflow(node_ids)

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
                        cached_histories,
                        workflow_nodes_needed,
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
        cached_histories: dict[str, WorkflowHistory] = None,
        workflow_nodes_needed: dict[str, list[str]] = None,
    ) -> dict[str, Any | None]:
        """
        Extract outputs for nodes that belong to a child workflow.

        This method:
        1. Gets child workflow's workflow_id and run_id from parent's history
        2. Fetches the child workflow's history (or reuses cached)
        3. Extracts node outputs from child workflow history

        Args:
            parent_history: The parent workflow history object
            child_workflow_id: The child workflow identifier (e.g., "ChildWorkflow#1")
            node_ids: List of node IDs in the child workflow
            cached_histories: Cache of already fetched workflow histories
            workflow_nodes_needed: Pre-collected map of workflow paths to their needed nodes

        Returns:
            Dictionary mapping node IDs to their outputs (None if not found)
        """
        if cached_histories is None:
            cached_histories = {}
        if workflow_nodes_needed is None:
            workflow_nodes_needed = {}

        # Get full path (e.g., "Parent#1.Child#1.activity#1" + "Child#1" -> "Parent#1.Child#1")
        full_child_path = self._get_workflow_path_from_node(node_ids[0], child_workflow_id)

        # Fetch child workflow history (traverses nested paths if needed)
        child_history = await self._fetch_nested_child_workflow_history(
            parent_history, full_child_path, node_ids, cached_histories, workflow_nodes_needed
        )

        if not child_history:
            return {node_id: None for node_id in node_ids}

        # Extract outputs using full node IDs (workflow stores with prefix, e.g., "Parent#1.activity#1")
        child_nodes_data = child_history.get_nodes_data()
        node_outputs = {}

        for full_node_id in node_ids:
            if full_node_id in child_nodes_data:
                node_outputs[full_node_id] = child_nodes_data[full_node_id].output_payload
            else:
                node_outputs[full_node_id] = None

        return node_outputs

    async def _fetch_nested_child_workflow_history(
        self,
        parent_history: WorkflowHistory,
        full_child_path: str,
        node_ids: list[str],
        cached_histories: dict[str, WorkflowHistory] = None,
        workflow_nodes_needed: dict[str, list[str]] = None,
    ) -> WorkflowHistory | None:
        """
        Fetch nested child workflow by traversing the path.
        E.g., "Parent#1.Child#1" fetches Parent#1, then Child#1 from Parent#1.
        """
        if cached_histories is None:
            cached_histories = {}
        if workflow_nodes_needed is None:
            workflow_nodes_needed = {}

        path_parts = full_child_path.split(".")
        current_history = parent_history

        for depth_level in range(len(path_parts)):
            current_path = ".".join(path_parts[: depth_level + 1])

            if current_path in cached_histories:
                current_history = cached_histories[current_path]
                continue

            # Get workflow_id and run_id from parent using full prefixed node_id
            workflow_id_run_id = current_history.get_child_workflow_workflow_id_run_id(current_path)
            if not workflow_id_run_id:
                return None

            workflow_id, run_id = workflow_id_run_id

            # Use pre-collected nodes or fallback
            if current_path in workflow_nodes_needed:
                fetch_node_ids = workflow_nodes_needed[current_path]
            else:
                is_final_level = depth_level == len(path_parts) - 1
                if is_final_level:
                    # Final level: fetch the actual nodes with full prefix
                    fetch_node_ids = node_ids
                else:
                    # Intermediate level: fetch the next child workflow with prefix
                    fetch_node_ids = [".".join(path_parts[: depth_level + 2])]

            # Fetch and cache
            current_history = await self._fetch_temporal_history(
                node_ids=fetch_node_ids, workflow_id=workflow_id, run_id=run_id
            )
            if not current_history:
                return None

            cached_histories[current_path] = current_history

        return current_history

    def _get_workflow_path_from_node(self, node_id: str, child_workflow_id: str) -> str:
        """
        Extract workflow path up to child_workflow_id from a node_id.
        E.g., node_id="Parent#1.Child#1.activity#1", child_workflow_id="Child#1" -> "Parent#1.Child#1"
        """
        parts = node_id.split(".")
        try:
            child_index = parts.index(child_workflow_id)
            return ".".join(parts[: child_index + 1])
        except ValueError:
            return child_workflow_id

    def _collect_nodes_per_workflow(self, node_ids: list[str]) -> dict[str, list[str]]:
        """
        Collect all node_ids needed from each workflow for batching (with workflow prefix).

        Input: ["Parent#1.query#1", "Parent#1.Child#1.activity#1"]
        Output: {"Parent#1": ["Parent#1.query#1", "Parent#1.Child#1"],
                 "Parent#1.Child#1": ["Parent#1.Child#1.activity#1"]}
        """
        workflow_nodes = {}

        for node_id in node_ids:
            parts = node_id.split(".")

            # For each level, collect what that workflow needs (with prefix)
            for i in range(1, len(parts)):
                workflow_path = ".".join(parts[:i])
                node_with_prefix = ".".join(parts[: i + 1])

                if workflow_path not in workflow_nodes:
                    workflow_nodes[workflow_path] = []

                if node_with_prefix not in workflow_nodes[workflow_path]:
                    workflow_nodes[workflow_path].append(node_with_prefix)

        return workflow_nodes

    def _group_nodes_by_parent_workflow(self, node_ids: list[str]) -> dict[str, list[str]]:
        """
        Group node IDs by their immediate parent workflow.
        - 'activity#1' -> parent = MAIN_WORKFLOW_IDENTIFIER
        - 'Child#1.activity#1' -> parent = 'Child#1'
        - 'Parent#1.Child#1.activity#1' -> parent = 'Child#1'
        """
        nodes_by_parent = {}

        for node_id in node_ids:
            parts = node_id.split(".")

            if len(parts) == 1:
                parent = MAIN_WORKFLOW_IDENTIFIER
            else:
                parent = parts[-2]  # Immediate parent is second-to-last

            if parent not in nodes_by_parent:
                nodes_by_parent[parent] = []
            nodes_by_parent[parent].append(node_id)

        return nodes_by_parent
