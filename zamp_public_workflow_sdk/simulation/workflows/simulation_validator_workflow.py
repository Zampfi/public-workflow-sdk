"""Workflow for validating simulation configurations by comparing inputs."""

import structlog
from collections import defaultdict
from deepdiff import DeepDiff

from zamp_public_workflow_sdk.actions_hub import ActionsHub
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    FetchTemporalWorkflowHistoryInput,
    FetchTemporalWorkflowHistoryOutput,
    WorkflowHistory,
)

from pantheon_v2.platform.temporal.workflow_validation.models import (
    ValidateWorkflowSimulationInput,
    ValidateWorkflowSimulationOutput,
    NodeInputComparison,
)

logger = structlog.get_logger(__name__)

MAIN_WORKFLOW_IDENTIFIER = "main_workflow"  # Identifier for top-level workflow nodes


@ActionsHub.register_workflow_defn(
    "Workflow that validates simulation by comparing inputs between golden and mocked workflows",
    labels=["temporal", "validation", "simulation"],
)
class ValidateWorkflowSimulationWorkflow:
    """
    Workflow that compares node inputs between a golden workflow and a mocked workflow
    to validate that simulation is working correctly.

    This workflow ONLY compares nodes that are specified in the simulation_config's mock_config.
    For each mocked node, it verifies that the node receives the same inputs in both:
    1. The reference workflow (with simulation enabled)
    2. The golden workflow (original execution without mocking)

    This ensures that the mocking/simulation layer is passing through the correct inputs
    to the mocked nodes, which is critical for simulation accuracy.

    Supports recursive child workflow validation with hierarchical node IDs like:
    - 'activity#1' (main workflow)
    - 'ChildWorkflow#1.activity#1' (child workflow activity)
    - 'Parent#1.Child#1.activity#1' (nested child workflow)
    """

    def __init__(self):
        """Initialize workflow with caches for fetched histories."""
        self.reference_workflow_histories: dict[str, WorkflowHistory] = {}
        self.golden_workflow_histories: dict[str, WorkflowHistory] = {}

    @ActionsHub.register_workflow_run
    async def execute(self, input: ValidateWorkflowSimulationInput) -> ValidateWorkflowSimulationOutput:
        """
        Execute workflow validation by comparing inputs.

        Args:
            input: Validation input containing workflow IDs and simulation config

        Returns:
            Validation output with comparison results
        """
        logger.info(
            "Starting ValidateWorkflowSimulationWorkflow",
            reference_workflow_id=input.reference_workflow_id,
            reference_run_id=input.reference_run_id,
            golden_workflow_id=input.golden_workflow_id,
            golden_run_id=input.golden_run_id,
        )

        # Step 1: Determine which nodes are mocked
        mocked_nodes = self._get_mocked_nodes(input.simulation_config)
        logger.info(
            "Identified mocked nodes",
            mocked_nodes=mocked_nodes,
            mocked_count=len(mocked_nodes),
        )

        # Step 2: Fetch main workflow histories from both workflows
        reference_history = await self._fetch_workflow_history(
            workflow_id=input.reference_workflow_id,
            run_id=input.reference_run_id,
            description="reference (mocked)",
        )
        self.reference_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = reference_history

        golden_history = await self._fetch_workflow_history(
            workflow_id=input.golden_workflow_id,
            run_id=input.golden_run_id,
            description="golden (original)",
        )
        self.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = golden_history

        # Step 3: Extract all nodes from both workflows
        reference_nodes = reference_history.get_nodes_data()
        golden_nodes = golden_history.get_nodes_data()

        logger.info(
            "Extracted nodes from main workflows",
            reference_nodes_count=len(reference_nodes),
            golden_nodes_count=len(golden_nodes),
            reference_node_ids=list(reference_nodes.keys()),
            golden_node_ids=list(golden_nodes.keys()),
        )

        # Step 4: Only compare nodes that are in mocked_nodes list
        # These are the nodes we want to validate are receiving the same inputs
        nodes_to_compare = mocked_nodes

        # Group nodes by their parent workflow to handle child workflows
        node_groups = self._group_nodes_by_parent_workflow(list(nodes_to_compare))
        logger.info(
            "Grouped mocked nodes by parent workflow",
            groups=list(node_groups.keys()),
            group_counts={k: len(v) for k, v in node_groups.items()},
            total_nodes_to_compare=len(nodes_to_compare),
            mocked_nodes=list(mocked_nodes),
        )

        # Collect which nodes are needed from each workflow level
        workflow_nodes_needed = self._collect_nodes_per_workflow(list(nodes_to_compare))

        # Step 5: Compare inputs for mocked nodes only (including child workflow nodes)
        comparisons = []
        matching_count = 0
        mismatched_count = 0
        error_count = 0

        for parent_workflow_id, workflow_node_ids in node_groups.items():
            if parent_workflow_id == MAIN_WORKFLOW_IDENTIFIER:
                # Main workflow nodes - compare directly
                for node_id in sorted(workflow_node_ids):
                    comparison = await self._compare_node_inputs(
                        node_id=node_id,
                        mocked_nodes=mocked_nodes,
                        reference_nodes=reference_nodes,
                        golden_nodes=golden_nodes,
                    )
                    comparisons.append(comparison)

                    if comparison.error:
                        error_count += 1
                    elif comparison.inputs_match is True and comparison.outputs_match is True:
                        matching_count += 1
                    elif comparison.inputs_match is False or comparison.outputs_match is False:
                        mismatched_count += 1
            else:
                # Child workflow nodes - need to fetch child histories
                logger.info(
                    "Processing child workflow nodes",
                    parent_workflow_id=parent_workflow_id,
                    node_count=len(workflow_node_ids),
                )

                child_comparisons = await self._compare_child_workflow_nodes(
                    parent_workflow_id=parent_workflow_id,
                    node_ids=workflow_node_ids,
                    mocked_nodes=mocked_nodes,
                    workflow_nodes_needed=workflow_nodes_needed,
                )

                for comparison in child_comparisons:
                    comparisons.append(comparison)
                    if comparison.error:
                        error_count += 1
                    elif comparison.inputs_match is True and comparison.outputs_match is True:
                        matching_count += 1
                    elif comparison.inputs_match is False or comparison.outputs_match is False:
                        mismatched_count += 1

        validation_passed = mismatched_count == 0 and error_count == 0

        logger.info(
            "Completed workflow validation",
            total_mocked_nodes_compared=len(comparisons),
            matching_nodes=matching_count,
            mismatched_nodes=mismatched_count,
            error_nodes=error_count,
            validation_passed=validation_passed,
        )

        # Create output
        output = ValidateWorkflowSimulationOutput(
            total_nodes_compared=len(comparisons),
            mocked_nodes_count=len(comparisons),  # All compared nodes are mocked nodes
            matching_nodes_count=matching_count,
            mismatched_nodes_count=mismatched_count,
            error_nodes_count=error_count,
            comparisons=comparisons,
            validation_passed=validation_passed,
        )

        # Save comparison results locally for debugging
        try:
            import json
            import os
            from datetime import datetime

            # Create output directory if it doesn't exist
            output_dir = "/tmp/workflow_validation_results"
            os.makedirs(output_dir, exist_ok=True)

            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_{input.reference_workflow_id[:8]}_{timestamp}.json"
            filepath = os.path.join(output_dir, filename)

            # Prepare data for JSON serialization
            result_data = {
                "validation_summary": {
                    "reference_workflow_id": input.reference_workflow_id,
                    "reference_run_id": input.reference_run_id,
                    "golden_workflow_id": input.golden_workflow_id,
                    "golden_run_id": input.golden_run_id,
                    "timestamp": timestamp,
                    "total_nodes_compared": len(comparisons),
                    "mocked_nodes_count": len(comparisons),  # All compared nodes are mocked
                    "matching_nodes_count": matching_count,
                    "mismatched_nodes_count": mismatched_count,
                    "error_nodes_count": error_count,
                    "validation_passed": validation_passed,
                },
                "mismatched_nodes_summary": [],
                "node_comparisons": [],
            }

            # Add detailed comparisons
            for comparison in comparisons:
                comp_data = {
                    "node_id": comparison.node_id,
                    "is_mocked": comparison.is_mocked,
                    "inputs_match": comparison.inputs_match,
                    "outputs_match": comparison.outputs_match,
                }

                # Include inputs and outputs for all nodes (all nodes being compared are mocked)
                comp_data["reference_input"] = comparison.reference_input
                comp_data["golden_input"] = comparison.golden_input
                comp_data["reference_output"] = comparison.reference_output
                comp_data["golden_output"] = comparison.golden_output

                if comparison.difference:
                    comp_data["difference"] = comparison.difference

                if comparison.output_difference:
                    comp_data["output_difference"] = comparison.output_difference

                if comparison.error:
                    comp_data["error"] = comparison.error

                result_data["node_comparisons"].append(comp_data)

            # Add mismatched nodes summary for easy debugging
            for comparison in comparisons:
                if (comparison.inputs_match is False or comparison.outputs_match is False) and not comparison.error:
                    summary_item = {
                        "node_id": comparison.node_id,
                        "inputs_match": comparison.inputs_match,
                        "outputs_match": comparison.outputs_match,
                    }

                    if comparison.inputs_match is False and comparison.difference:
                        summary_item["input_differences"] = comparison.difference

                    if comparison.outputs_match is False and comparison.output_difference:
                        summary_item["output_differences"] = comparison.output_difference

                    result_data["mismatched_nodes_summary"].append(summary_item)

            # Write to file
            with open(filepath, "w") as f:
                json.dump(result_data, f, indent=2, default=str)

            logger.info(
                "Saved validation results locally",
                filepath=filepath,
                total_comparisons=len(comparisons),
            )
        except Exception as e:
            logger.error(
                "Failed to save validation results locally",
                error=str(e),
                error_type=type(e).__name__,
            )

        return output

    def _get_mocked_nodes(self, simulation_config) -> set[str]:
        """
        Extract list of mocked node IDs from simulation config.

        Args:
            simulation_config: Simulation configuration

        Returns:
            Set of mocked node IDs
        """
        mocked_nodes = set()

        if not simulation_config or not simulation_config.mock_config:
            return mocked_nodes

        for node_strategy in simulation_config.mock_config.node_strategies:
            # Add all nodes from this strategy to the mocked set
            mocked_nodes.update(node_strategy.nodes)

        return mocked_nodes

    async def _fetch_workflow_history(
        self, workflow_id: str, run_id: str, description: str
    ) -> FetchTemporalWorkflowHistoryOutput:
        """
        Fetch workflow history using the FetchTemporalWorkflowHistoryWorkflow.

        Args:
            workflow_id: Workflow ID to fetch
            run_id: Run ID to fetch
            description: Description for logging

        Returns:
            Workflow history
        """
        logger.info(
            f"Fetching {description} workflow history",
            workflow_id=workflow_id,
            run_id=run_id,
        )

        try:
            history = await ActionsHub.execute_child_workflow(
                "FetchTemporalWorkflowHistoryWorkflow",
                FetchTemporalWorkflowHistoryInput(
                    workflow_id=workflow_id,
                    run_id=run_id,
                ),
                result_type=FetchTemporalWorkflowHistoryOutput,
            )

            logger.info(
                f"Successfully fetched {description} workflow history",
                workflow_id=workflow_id,
                run_id=run_id,
                events_count=len(history.events),
            )

            return history

        except Exception as e:
            logger.error(
                f"Failed to fetch {description} workflow history",
                workflow_id=workflow_id,
                run_id=run_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def _compare_node_inputs(
        self,
        node_id: str,
        mocked_nodes: set[str],
        reference_nodes: dict,
        golden_nodes: dict,
    ) -> NodeInputComparison:
        """
        Compare inputs for a single node between reference and golden workflows.

        For mocked nodes, we verify that they receive the same inputs in both workflows.
        This validates that the simulation is working correctly.

        Supports hierarchical node IDs for child workflows (e.g., "ChildWorkflow#1.activity#1").

        Args:
            node_id: Node ID to compare (can be hierarchical)
            mocked_nodes: Set of mocked node IDs (these WILL be compared)
            reference_nodes: Node data from reference workflow
            golden_nodes: Node data from golden workflow

        Returns:
            Comparison result
        """
        is_mocked = node_id in mocked_nodes

        try:
            # Get node data from both workflows
            reference_node = reference_nodes.get(node_id)
            golden_node = golden_nodes.get(node_id)

            # Check if node exists in both workflows
            if not reference_node:
                logger.warning(
                    "Node not found in reference workflow",
                    node_id=node_id,
                )
                return NodeInputComparison(
                    node_id=node_id,
                    is_mocked=False,
                    inputs_match=None,
                    outputs_match=None,
                    error="Node not found in reference workflow",
                )

            if not golden_node:
                logger.warning(
                    "Node not found in golden workflow",
                    node_id=node_id,
                )
                return NodeInputComparison(
                    node_id=node_id,
                    is_mocked=False,
                    inputs_match=None,
                    outputs_match=None,
                    error="Node not found in golden workflow",
                )

            # Extract inputs and outputs
            reference_input = reference_node.input_payload
            golden_input = golden_node.input_payload
            reference_output = reference_node.output_payload
            golden_output = golden_node.output_payload

            # Compare inputs using DeepDiff
            input_diff = DeepDiff(
                golden_input,
                reference_input,
                ignore_order=False,
                verbose_level=2,
            )

            inputs_match = len(input_diff) == 0

            # Compare outputs using DeepDiff
            output_diff = DeepDiff(
                golden_output,
                reference_output,
                ignore_order=False,
                verbose_level=2,
            )

            outputs_match = len(output_diff) == 0

            if inputs_match and outputs_match:
                logger.info(
                    "✅ Node inputs and outputs match",
                    node_id=node_id,
                    is_mocked=is_mocked,
                    reference_input_type=type(reference_input).__name__ if reference_input is not None else None,
                    golden_input_type=type(golden_input).__name__ if golden_input is not None else None,
                    reference_output_type=type(reference_output).__name__ if reference_output is not None else None,
                    golden_output_type=type(golden_output).__name__ if golden_output is not None else None,
                )
                return NodeInputComparison(
                    node_id=node_id,
                    is_mocked=is_mocked,
                    inputs_match=True,
                    outputs_match=True,
                    reference_input=reference_input,
                    golden_input=golden_input,
                    reference_output=reference_output,
                    golden_output=golden_output,
                )
            else:
                logger.warning(
                    "❌ Node inputs or outputs do not match",
                    node_id=node_id,
                    is_mocked=is_mocked,
                    inputs_match=inputs_match,
                    outputs_match=outputs_match,
                    input_difference=input_diff if not inputs_match else None,
                    output_difference=output_diff if not outputs_match else None,
                    reference_input_type=type(reference_input).__name__ if reference_input is not None else None,
                    golden_input_type=type(golden_input).__name__ if golden_input is not None else None,
                    reference_output_type=type(reference_output).__name__ if reference_output is not None else None,
                    golden_output_type=type(golden_output).__name__ if golden_output is not None else None,
                )
                return NodeInputComparison(
                    node_id=node_id,
                    is_mocked=is_mocked,
                    inputs_match=inputs_match,
                    outputs_match=outputs_match,
                    reference_input=reference_input,
                    golden_input=golden_input,
                    reference_output=reference_output,
                    golden_output=golden_output,
                    difference=dict(input_diff) if not inputs_match else None,
                    output_difference=dict(output_diff) if not outputs_match else None,
                )

        except Exception as e:
            logger.error(
                "Error comparing node inputs and outputs",
                node_id=node_id,
                is_mocked=is_mocked,
                error=str(e),
                error_type=type(e).__name__,
            )
            return NodeInputComparison(
                node_id=node_id,
                is_mocked=is_mocked,
                inputs_match=None,
                outputs_match=None,
                error=f"Comparison error: {str(e)}",
            )

    async def _compare_child_workflow_nodes(
        self,
        parent_workflow_id: str,
        node_ids: list[str],
        mocked_nodes: set[str],
        workflow_nodes_needed: dict[str, list[str]],
    ) -> list[NodeInputComparison]:
        """
        Compare inputs for nodes that belong to a child workflow.

        This method:
        1. Gets child workflow's workflow_id and run_id from parent's history
        2. Fetches the child workflow's history for both reference and golden
        3. Extracts node inputs from child workflow histories
        4. Compares inputs between reference and golden child workflows

        Args:
            parent_workflow_id: The parent workflow identifier (e.g., "ChildWorkflow#1")
            node_ids: List of node IDs in the child workflow
            mocked_nodes: Set of mocked node IDs
            workflow_nodes_needed: Pre-collected map of workflow paths to their needed nodes

        Returns:
            List of comparison results for all child workflow nodes
        """
        comparisons = []

        # Extract the full path to the child workflow
        full_child_path = self._get_workflow_path_from_node(node_ids[0], parent_workflow_id)
        logger.info(
            "Processing child workflow",
            full_child_path=full_child_path,
            node_count=len(node_ids),
        )

        try:
            # Fetch child workflow histories for both reference and golden
            reference_child_history = await self._fetch_nested_child_workflow_history(
                parent_workflow_history=self.reference_workflow_histories[MAIN_WORKFLOW_IDENTIFIER],
                full_child_path=full_child_path,
                node_ids=node_ids,
                workflow_nodes_needed=workflow_nodes_needed,
                is_reference=True,
            )

            golden_child_history = await self._fetch_nested_child_workflow_history(
                parent_workflow_history=self.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER],
                full_child_path=full_child_path,
                node_ids=node_ids,
                workflow_nodes_needed=workflow_nodes_needed,
                is_reference=False,
            )

            # Extract nodes from child workflows
            reference_child_nodes = reference_child_history.get_nodes_data()
            golden_child_nodes = golden_child_history.get_nodes_data()

            logger.info(
                "Extracted nodes from child workflows",
                full_child_path=full_child_path,
                reference_count=len(reference_child_nodes),
                golden_count=len(golden_child_nodes),
            )

            # Compare each node in the child workflow
            for node_id in sorted(node_ids):
                comparison = await self._compare_node_inputs(
                    node_id=node_id,
                    mocked_nodes=mocked_nodes,
                    reference_nodes=reference_child_nodes,
                    golden_nodes=golden_child_nodes,
                )
                comparisons.append(comparison)

        except Exception as e:
            logger.error(
                "Error comparing child workflow nodes",
                parent_workflow_id=parent_workflow_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return error comparisons for all nodes
            for node_id in node_ids:
                comparisons.append(
                    NodeInputComparison(
                        node_id=node_id,
                        is_mocked=node_id in mocked_nodes,
                        inputs_match=None,
                        outputs_match=None,
                        error=f"Failed to fetch child workflow history: {str(e)}",
                    )
                )

        return comparisons

    async def _fetch_nested_child_workflow_history(
        self,
        parent_workflow_history: WorkflowHistory,
        full_child_path: str,
        node_ids: list[str],
        workflow_nodes_needed: dict[str, list[str]],
        is_reference: bool,
    ) -> WorkflowHistory:
        """
        Fetch nested child workflow by traversing the path.
        E.g., "Parent#1.Child#1" fetches Parent#1, then Child#1 from Parent#1.

        Args:
            parent_workflow_history: Starting parent workflow history
            full_child_path: Full path to child workflow (e.g., "Parent#1.Child#1")
            node_ids: List of node IDs to fetch
            workflow_nodes_needed: Pre-collected nodes per workflow
            is_reference: True for reference workflow, False for golden

        Returns:
            Workflow history for the nested child workflow
        """
        workflow_histories = self.reference_workflow_histories if is_reference else self.golden_workflow_histories

        path_parts = full_child_path.split(".")
        current_history = parent_workflow_history

        for depth_level in range(len(path_parts)):
            current_path = ".".join(path_parts[: depth_level + 1])

            # Check if we already have this workflow's history cached
            if current_path in workflow_histories:
                current_history = workflow_histories[current_path]
                logger.info(
                    "Using cached history",
                    current_path=current_path,
                    is_reference=is_reference,
                )
                continue

            # Get workflow_id and run_id from parent using full prefixed node_id
            try:
                workflow_id, run_id = current_history.get_child_workflow_workflow_id_run_id(current_path)
            except ValueError as e:
                raise Exception(
                    f"Failed to get workflow_id and run_id for child workflow at path={current_path}. "
                    f"Child workflow execution may not have started or node_id may be invalid. "
                    f"Original error: {str(e)}"
                ) from e

            # # Determine which nodes to fetch
            # if current_path in workflow_nodes_needed:
            #     fetch_node_ids = workflow_nodes_needed[current_path]
            # else:
            #     is_final_level = depth_level == len(path_parts) - 1
            #     if is_final_level:
            #         # Final level: fetch the actual nodes with full prefix
            #         fetch_node_ids = node_ids
            #     else:
            #         # Intermediate level: fetch the next child workflow with prefix
            #         fetch_node_ids = [".".join(path_parts[: depth_level + 2])]

            # Fetch and cache child workflow history
            logger.info(
                "Fetching child workflow history",
                current_path=current_path,
                workflow_id=workflow_id,
                run_id=run_id,
                is_reference=is_reference,
            )

            current_history = await self._fetch_workflow_history(
                workflow_id=workflow_id,
                run_id=run_id,
                description=f"{'reference' if is_reference else 'golden'} child workflow {current_path}",
            )

            # Cache the fetched history
            workflow_histories[current_path] = current_history

        return current_history

    def _group_nodes_by_parent_workflow(self, node_ids: list[str]) -> dict[str, list[str]]:
        """
        Group node IDs by their immediate parent workflow using full path.

        Examples:
        - 'activity#1' -> parent = MAIN_WORKFLOW_IDENTIFIER
        - 'Child#1.activity#1' -> parent = 'Child#1'
        - 'Parent#1.Child#1.activity#1' -> parent = 'Parent#1.Child#1'
        - 'A#1.B#1.C#1.activity#1' -> parent = 'A#1.B#1.C#1'

        This ensures that multiple instances of the same workflow name in different
        parts of the hierarchy are grouped separately.

        Args:
            node_ids: List of node IDs (can be hierarchical)

        Returns:
            Dictionary mapping parent workflow IDs to lists of node IDs
        """
        node_groups = defaultdict(list)

        for node_id in node_ids:
            parts = node_id.split(".")

            if len(parts) == 1:
                # Top-level node in main workflow
                parent = MAIN_WORKFLOW_IDENTIFIER
            else:
                # Use full path up to (but not including) the last part
                parent = ".".join(parts[:-1])

            node_groups[parent].append(node_id)

        return dict(node_groups)

    def _collect_nodes_per_workflow(self, node_ids: list[str]) -> dict[str, list[str]]:
        """
        Collect all node_ids needed from each workflow for batching (with workflow prefix).

        This helps optimize fetching by knowing which nodes are needed at each level.

        Example:
            Input: ["Parent#1.query#1", "Parent#1.Child#1.activity#1"]
            Output: {
                "Parent#1": ["Parent#1.query#1", "Parent#1.Child#1"],
                "Parent#1.Child#1": ["Parent#1.Child#1.activity#1"]
            }

        Args:
            node_ids: List of node IDs (can be hierarchical)

        Returns:
            Dictionary mapping workflow paths to lists of node IDs needed at that level
        """
        workflow_nodes = {}

        for node_id in node_ids:
            parts = node_id.split(".")

            # For each level, collect what that workflow needs (with prefix)
            for depth_level in range(1, len(parts)):
                workflow_path = ".".join(parts[:depth_level])
                node_with_prefix = ".".join(parts[: depth_level + 1])

                # Initialize workflow path if not seen before
                if workflow_path not in workflow_nodes:
                    workflow_nodes[workflow_path] = []

                # Skip if this node is already in the list
                if node_with_prefix in workflow_nodes[workflow_path]:
                    continue

                workflow_nodes[workflow_path].append(node_with_prefix)

        return workflow_nodes

    def _get_workflow_path_from_node(self, node_id: str, child_workflow_id: str) -> str:
        """
        Extract the full path to the child workflow from a node ID.

        Given a node like "Parent#1.Child#1.activity#1" and child_workflow_id "Child#1",
        this returns "Parent#1.Child#1" (the path up to and including the child workflow).

        Args:
            node_id: Full node ID (e.g., "Parent#1.Child#1.activity#1")
            child_workflow_id: Child workflow identifier (e.g., "Child#1")

        Returns:
            Full path to the child workflow
        """
        parts = node_id.split(".")

        # Find where the child_workflow_id appears and return path up to that point
        for i, part in enumerate(parts):
            if child_workflow_id in part:
                return ".".join(parts[: i + 1])

        # If child_workflow_id is not found, return the full path minus the last part
        return ".".join(parts[:-1])
