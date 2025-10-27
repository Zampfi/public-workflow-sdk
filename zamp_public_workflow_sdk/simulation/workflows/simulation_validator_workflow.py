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

from zamp_public_workflow_sdk.simulation.models.simulation_validation import (
    SimulationValidatorInput,
    SimulationValidatorOutput,
    NodeComparison,
    MismatchedNodeSummary,
)

logger = structlog.get_logger(__name__)

MAIN_WORKFLOW_IDENTIFIER = "main_workflow"


@ActionsHub.register_workflow_defn(
    "Workflow that validates simulation by comparing inputs between golden and mocked workflows",
    labels=["temporal", "validation", "simulation"],
)
class SimulationValidatorWorkflow:
    """
    Validates simulation accuracy by comparing node inputs/outputs between golden and mocked workflows.

    Compares only nodes specified in simulation_config's mock_config to verify the simulation
    layer passes correct inputs to mocked nodes. Supports hierarchical child workflows.
    """

    def __init__(self):
        """Initialize workflow with caches for fetched histories."""
        self.reference_workflow_histories: dict[str, WorkflowHistory] = {}
        self.golden_workflow_histories: dict[str, WorkflowHistory] = {}

    @ActionsHub.register_workflow_run
    async def execute(self, input: SimulationValidatorInput) -> SimulationValidatorOutput:
        """Execute workflow validation by comparing inputs and outputs."""
        logger.info(
            "Starting validation",
            reference_workflow_id=input.reference_workflow_id,
            golden_workflow_id=input.golden_workflow_id,
        )

        mocked_nodes = self._get_mocked_nodes(input.simulation_config)
        if not mocked_nodes:
            logger.warning("No mocked nodes found in simulation config")
            return self._build_empty_output()

        logger.info("Identified mocked nodes", count=len(mocked_nodes))

        await self._fetch_and_cache_main_workflows(input)
        comparisons = await self._compare_all_nodes(mocked_nodes)
        output = self._build_output(comparisons)

        logger.info(
            "Validation completed",
            total_compared=output.total_nodes_compared,
            matching=output.matching_nodes_count,
            mismatched=output.mismatched_nodes_count,
            errors=output.error_nodes_count,
            passed=output.validation_passed,
        )

        return output

    async def _fetch_and_cache_main_workflows(self, input: SimulationValidatorInput) -> None:
        """Fetch and cache main workflow histories for both reference and golden."""
        reference_history = await self._fetch_workflow_history(
            workflow_id=input.reference_workflow_id,
            run_id=input.reference_run_id,
            description="reference",
        )
        self.reference_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = reference_history

        golden_history = await self._fetch_workflow_history(
            workflow_id=input.golden_workflow_id,
            run_id=input.golden_run_id,
            description="golden",
        )
        self.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = golden_history

    async def _compare_all_nodes(self, mocked_nodes: set[str]) -> list[NodeComparison]:
        """Compare all mocked nodes across main and child workflows."""
        node_groups = self._group_nodes_by_parent_workflow(list(mocked_nodes))
        comparisons = []

        for parent_workflow_id, node_ids in node_groups.items():
            if parent_workflow_id == MAIN_WORKFLOW_IDENTIFIER:
                comparisons.extend(await self._compare_main_workflow_nodes(node_ids, mocked_nodes))
            else:
                comparisons.extend(await self._compare_child_workflow_nodes(parent_workflow_id, node_ids, mocked_nodes))

        return comparisons

    async def _compare_main_workflow_nodes(self, node_ids: list[str], mocked_nodes: set[str]) -> list[NodeComparison]:
        """Compare nodes in the main workflow."""
        reference_nodes = self.reference_workflow_histories[MAIN_WORKFLOW_IDENTIFIER].get_nodes_data()
        golden_nodes = self.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER].get_nodes_data()

        return [
            await self._compare_node(node_id, mocked_nodes, reference_nodes, golden_nodes)
            for node_id in sorted(node_ids)
        ]

    def _build_output(self, comparisons: list[NodeComparison]) -> SimulationValidatorOutput:
        """Build validation output with statistics and mismatch summary."""
        matching_count = 0
        mismatched_count = 0
        error_count = 0
        mismatched_nodes_summary = []

        for comparison in comparisons:
            if comparison.error:
                error_count += 1
            elif comparison.inputs_match and comparison.outputs_match:
                matching_count += 1
            else:
                mismatched_count += 1
                mismatched_nodes_summary.append(
                    MismatchedNodeSummary(
                        node_id=comparison.node_id,
                        inputs_match=comparison.inputs_match,
                        outputs_match=comparison.outputs_match,
                        input_differences=comparison.difference if not comparison.inputs_match else None,
                        output_differences=comparison.output_difference if not comparison.outputs_match else None,
                    )
                )

        return SimulationValidatorOutput(
            total_nodes_compared=len(comparisons),
            mocked_nodes_count=len(comparisons),
            matching_nodes_count=matching_count,
            mismatched_nodes_count=mismatched_count,
            error_nodes_count=error_count,
            mismatched_nodes_summary=mismatched_nodes_summary,
            comparisons=comparisons,
            validation_passed=(mismatched_count == 0 and error_count == 0),
        )

    def _build_empty_output(self) -> SimulationValidatorOutput:
        """Build empty output when no nodes to compare."""
        return SimulationValidatorOutput(
            total_nodes_compared=0,
            mocked_nodes_count=0,
            matching_nodes_count=0,
            mismatched_nodes_count=0,
            error_nodes_count=0,
            mismatched_nodes_summary=[],
            comparisons=[],
            validation_passed=True,
        )

    def _get_mocked_nodes(self, simulation_config) -> set[str]:
        """Extract list of mocked node IDs from simulation config."""
        if not simulation_config or not simulation_config.mock_config:
            return set()

        mocked_nodes = set()
        for node_strategy in simulation_config.mock_config.node_strategies:
            mocked_nodes.update(node_strategy.nodes)
        return mocked_nodes

    async def _fetch_workflow_history(self, workflow_id: str, run_id: str, description: str) -> WorkflowHistory:
        """Fetch workflow history using the FetchTemporalWorkflowHistoryWorkflow."""
        logger.info("Fetching workflow history", description=description, workflow_id=workflow_id)

        try:
            history = await ActionsHub.execute_child_workflow(
                "FetchTemporalWorkflowHistoryWorkflow",
                FetchTemporalWorkflowHistoryInput(workflow_id=workflow_id, run_id=run_id),
                result_type=FetchTemporalWorkflowHistoryOutput,
            )
            logger.info("Fetched workflow history", description=description, events_count=len(history.events))
            return history
        except Exception as e:
            logger.error("Failed to fetch workflow history", description=description, error=str(e))
            raise

    def _create_error_comparison(self, node_id: str, is_mocked: bool, error: str) -> NodeComparison:
        """Create a NodeInputComparison object for error cases."""
        return NodeComparison(
            node_id=node_id,
            is_mocked=is_mocked,
            inputs_match=None,
            outputs_match=None,
            error=error,
        )

    async def _compare_node(
        self,
        node_id: str,
        mocked_nodes: set[str],
        reference_nodes: dict,
        golden_nodes: dict,
    ) -> NodeComparison:
        """Compare inputs and outputs for a single node between reference and golden workflows."""
        is_mocked = node_id in mocked_nodes

        try:
            reference_node = reference_nodes.get(node_id)
            if not reference_node:
                logger.warning("Node not found in reference workflow", node_id=node_id)
                return self._create_error_comparison(node_id, is_mocked, "Node not found in reference workflow")

            golden_node = golden_nodes.get(node_id)
            if not golden_node:
                logger.warning("Node not found in golden workflow", node_id=node_id)
                return self._create_error_comparison(node_id, is_mocked, "Node not found in golden workflow")

            # Compare inputs and outputs
            input_diff = DeepDiff(
                golden_node.input_payload,
                reference_node.input_payload,
                ignore_order=False,
                verbose_level=2,
            )
            output_diff = DeepDiff(
                golden_node.output_payload,
                reference_node.output_payload,
                ignore_order=False,
                verbose_level=2,
            )

            inputs_match = len(input_diff) == 0
            outputs_match = len(output_diff) == 0

            log_level = logger.info if inputs_match and outputs_match else logger.warning
            log_level("Node comparison", node_id=node_id, inputs_match=inputs_match, outputs_match=outputs_match)

            return NodeComparison(
                node_id=node_id,
                is_mocked=is_mocked,
                inputs_match=inputs_match,
                outputs_match=outputs_match,
                reference_input=reference_node.input_payload,
                golden_input=golden_node.input_payload,
                reference_output=reference_node.output_payload,
                golden_output=golden_node.output_payload,
                difference=dict(input_diff) if not inputs_match else None,
                output_difference=dict(output_diff) if not outputs_match else None,
            )

        except Exception as e:
            logger.error("Error comparing node", node_id=node_id, error=str(e))
            return self._create_error_comparison(node_id, is_mocked, f"Comparison error: {str(e)}")

    async def _compare_child_workflow_nodes(
        self,
        parent_workflow_id: str,
        node_ids: list[str],
        mocked_nodes: set[str],
    ) -> list[NodeComparison]:
        """Compare inputs for nodes that belong to a child workflow."""
        full_child_path = self._get_workflow_path_from_node(node_ids[0], parent_workflow_id)
        logger.info("Processing child workflow", full_child_path=full_child_path, node_count=len(node_ids))

        try:
            # Fetch child workflow histories
            reference_child_history = await self._fetch_nested_child_workflow_history(
                parent_workflow_history=self.reference_workflow_histories[MAIN_WORKFLOW_IDENTIFIER],
                full_child_path=full_child_path,
                is_reference=True,
            )

            golden_child_history = await self._fetch_nested_child_workflow_history(
                parent_workflow_history=self.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER],
                full_child_path=full_child_path,
                is_reference=False,
            )

            # Extract and compare nodes
            reference_child_nodes = reference_child_history.get_nodes_data()
            golden_child_nodes = golden_child_history.get_nodes_data()

            return [
                await self._compare_node(node_id, mocked_nodes, reference_child_nodes, golden_child_nodes)
                for node_id in sorted(node_ids)
            ]

        except Exception as e:
            logger.error("Error comparing child workflow nodes", parent_workflow_id=parent_workflow_id, error=str(e))
            return [
                self._create_error_comparison(
                    node_id, node_id in mocked_nodes, f"Failed to fetch child workflow history: {str(e)}"
                )
                for node_id in node_ids
            ]

    async def _fetch_nested_child_workflow_history(
        self,
        parent_workflow_history: WorkflowHistory,
        full_child_path: str,
        is_reference: bool,
    ) -> WorkflowHistory:
        """
        Fetch nested child workflow by traversing the path.
        E.g., "Parent#1.Child#1" fetches Parent#1, then Child#1 from Parent#1.
        """
        workflow_histories = self.reference_workflow_histories if is_reference else self.golden_workflow_histories
        path_parts = full_child_path.split(".")
        current_history = parent_workflow_history

        for depth_level in range(len(path_parts)):
            current_path = ".".join(path_parts[: depth_level + 1])

            # Check cache
            if current_path in workflow_histories:
                current_history = workflow_histories[current_path]
                continue

            # Get workflow IDs and fetch history
            try:
                workflow_id, run_id = current_history.get_child_workflow_workflow_id_run_id(current_path)
            except ValueError as e:
                raise Exception(
                    f"Failed to get workflow_id and run_id for child workflow at path={current_path}. "
                    f"Child workflow execution may not have started or node_id may be invalid. "
                    f"Original error: {str(e)}"
                ) from e

            current_history = await self._fetch_workflow_history(
                workflow_id=workflow_id,
                run_id=run_id,
                description=f"{'reference' if is_reference else 'golden'} child {current_path}",
            )

            workflow_histories[current_path] = current_history

        return current_history

    def _group_nodes_by_parent_workflow(self, node_ids: list[str]) -> dict[str, list[str]]:
        """
        Group node IDs by their immediate parent workflow.

        Examples:
            'activity#1' -> MAIN_WORKFLOW_IDENTIFIER
            'Child#1.activity#1' -> 'Child#1'
            'Parent#1.Child#1.activity#1' -> 'Parent#1.Child#1'
        """
        node_groups = defaultdict(list)
        for node_id in node_ids:
            parts = node_id.split(".")
            parent = MAIN_WORKFLOW_IDENTIFIER if len(parts) == 1 else ".".join(parts[:-1])
            node_groups[parent].append(node_id)
        return dict(node_groups)

    def _get_workflow_path_from_node(self, node_id: str, child_workflow_id: str) -> str:
        """
        Extract the full path to the child workflow from a node ID.

        Example: "Parent#1.Child#1.activity#1" with child_workflow_id "Child#1" -> "Parent#1.Child#1"
        """
        parts = node_id.split(".")
        for i, part in enumerate(parts):
            if child_workflow_id in part:
                return ".".join(parts[: i + 1])
        return ".".join(parts[:-1])
