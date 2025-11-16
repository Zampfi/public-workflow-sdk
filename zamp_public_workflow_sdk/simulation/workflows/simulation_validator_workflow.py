from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import structlog
    import json
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
        self.simulation_workflow_histories: dict[str, WorkflowHistory] = {}
        self.golden_workflow_histories: dict[str, WorkflowHistory] = {}

    @ActionsHub.register_workflow_run
    async def execute(self, input: SimulationValidatorInput) -> SimulationValidatorOutput:
        """Execute workflow validation by comparing inputs and outputs."""
        logger.info(
            "Starting validation",
            simulation_workflow_id=input.simulation_workflow_id,
            golden_workflow_id=input.golden_workflow_id,
        )

        mocked_nodes = self._get_mocked_nodes(input.simulation_config)
        if not mocked_nodes:
            logger.warning("No mocked nodes found in simulation config")
            return SimulationValidatorOutput(
                total_nodes_compared=0,
                mocked_nodes_count=0,
                matching_nodes_count=0,
                mismatched_nodes_count=0,
                mismatched_node_ids=None,
                comparison_error_nodes_count=0,
                comparison_error_node_ids=None,
                nodes_missing_in_simulation_workflow=None,
                nodes_missing_in_golden_workflow=None,
                comparisons=[],
                validation_passed=True,
            )

        logger.info("Identified mocked nodes", count=len(mocked_nodes))

        await self._fetch_and_cache_main_workflows(input)
        comparisons = await self._compare_all_nodes(mocked_nodes)
        output = self._build_output(comparisons)

        logger.info(
            "Validation completed",
            total_compared=output.total_nodes_compared,
            matching=output.matching_nodes_count,
            mismatched=output.mismatched_nodes_count,
            comparison_errors=output.comparison_error_nodes_count,
            missing_in_simulation=len(output.nodes_missing_in_simulation_workflow or []),
            missing_in_golden=len(output.nodes_missing_in_golden_workflow or []),
            passed=output.validation_passed,
        )

        return output

    async def _fetch_and_cache_main_workflows(self, input: SimulationValidatorInput) -> None:
        """Fetch and cache main workflow histories for both simulation and golden."""
        simulation_history = await self._fetch_workflow_history(
            workflow_id=input.simulation_workflow_id,
            run_id=input.simulation_workflow_run_id,
            description="simulation",
        )
        self.simulation_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = simulation_history

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
        simulation_nodes = self.simulation_workflow_histories[MAIN_WORKFLOW_IDENTIFIER].get_nodes_data()
        golden_nodes = self.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER].get_nodes_data()

        return [
            await self._compare_node(node_id, mocked_nodes, simulation_nodes, golden_nodes)
            for node_id in sorted(node_ids)
        ]

    def _build_output(self, comparisons: list[NodeComparison]) -> SimulationValidatorOutput:
        """Build validation output with statistics and mismatch summary."""
        matching_count = 0
        mismatched_count = 0
        comparison_error_count = 0
        mismatched_node_ids = []
        comparison_error_node_ids = []
        nodes_missing_in_simulation = []
        nodes_missing_in_golden = []

        for comparison in comparisons:
            if comparison.error:
                comparison_error_count += 1
                comparison_error_node_ids.append(comparison.node_id)

                # Check if it's a missing node error
                if "not found in simulation workflow" in comparison.error:
                    nodes_missing_in_simulation.append(comparison.node_id)
                elif "not found in golden workflow" in comparison.error:
                    nodes_missing_in_golden.append(comparison.node_id)
            elif comparison.inputs_match and comparison.outputs_match:
                matching_count += 1
            else:
                mismatched_count += 1
                mismatched_node_ids.append(comparison.node_id)

        return SimulationValidatorOutput(
            total_nodes_compared=len(comparisons),
            mocked_nodes_count=len(comparisons),
            matching_nodes_count=matching_count,
            mismatched_nodes_count=mismatched_count,
            mismatched_node_ids=mismatched_node_ids if mismatched_node_ids else None,
            comparison_error_nodes_count=comparison_error_count,
            comparison_error_node_ids=comparison_error_node_ids if comparison_error_node_ids else None,
            nodes_missing_in_simulation_workflow=nodes_missing_in_simulation if nodes_missing_in_simulation else None,
            nodes_missing_in_golden_workflow=nodes_missing_in_golden if nodes_missing_in_golden else None,
            comparisons=comparisons,
            validation_passed=(mismatched_count == 0 and comparison_error_count == 0),
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
                FetchTemporalWorkflowHistoryInput(workflow_id=workflow_id, run_id=run_id, decode_payloads=True),
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

    def _convert_diff_to_dict(self, diff, diff_type: str, node_id: str) -> dict | None:
        """
        Convert DeepDiff to dict by removing type_changes
        Returns the dict if serializable, None otherwise.
        """
        try:
            diff_as_dict = dict(diff)
            diff_as_dict.pop("type_changes", None)
            json.dumps(diff_as_dict)
            return diff_as_dict
        except Exception as e:
            logger.warning(
                "Could not serialize difference",
                diff_type=diff_type,
                node_id=node_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def _compare_node(
        self,
        node_id: str,
        mocked_nodes: set[str],
        simulation_nodes: dict,
        golden_nodes: dict,
    ) -> NodeComparison:
        """Compare inputs and outputs for a single node between reference and golden workflows."""
        is_mocked = node_id in mocked_nodes

        try:
            simulation_node = simulation_nodes.get(node_id)
            if not simulation_node:
                logger.warning("Node not found in simulation workflow", node_id=node_id)
                return self._create_error_comparison(node_id, is_mocked, "Node not found in simulation workflow")

            golden_node = golden_nodes.get(node_id)
            if not golden_node:
                logger.warning("Node not found in golden workflow", node_id=node_id)
                return self._create_error_comparison(node_id, is_mocked, "Node not found in golden workflow")

            # Compare inputs and outputs
            input_diff = DeepDiff(
                golden_node.input_payload,
                simulation_node.input_payload,
                ignore_order=False,
                verbose_level=2,
            )
            output_diff = DeepDiff(
                golden_node.output_payload,
                simulation_node.output_payload,
                ignore_order=False,
                verbose_level=2,
            )

            inputs_match = len(input_diff) == 0
            outputs_match = len(output_diff) == 0

            logger.info("Node comparison", node_id=node_id, inputs_match=inputs_match, outputs_match=outputs_match)

            difference_dict = self._convert_diff_to_dict(input_diff, "input", node_id) if not inputs_match else None
            output_difference_dict = (
                self._convert_diff_to_dict(output_diff, "output", node_id) if not outputs_match else None
            )

            return NodeComparison(
                node_id=node_id,
                is_mocked=is_mocked,
                inputs_match=inputs_match,
                outputs_match=outputs_match,
                actual_input=simulation_node.input_payload,
                expected_input=golden_node.input_payload,
                actual_output=simulation_node.output_payload,
                expected_output=golden_node.output_payload,
                difference=difference_dict,
                output_difference=output_difference_dict,
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
            simulation_child_history = await self._fetch_nested_child_workflow_history(
                parent_workflow_history=self.simulation_workflow_histories[MAIN_WORKFLOW_IDENTIFIER],
                full_child_path=full_child_path,
                is_simulation=True,
            )

            golden_child_history = await self._fetch_nested_child_workflow_history(
                parent_workflow_history=self.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER],
                full_child_path=full_child_path,
                is_simulation=False,
            )

            # Extract and compare nodes
            simulation_child_nodes = simulation_child_history.get_nodes_data()
            golden_child_nodes = golden_child_history.get_nodes_data()

            return [
                await self._compare_node(node_id, mocked_nodes, simulation_child_nodes, golden_child_nodes)
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
        is_simulation: bool,
    ) -> WorkflowHistory:
        """
        Fetch nested child workflow by traversing the path.
        E.g., "Parent#1.Child#1" fetches Parent#1, then Child#1 from Parent#1.
        """
        workflow_histories = self.simulation_workflow_histories if is_simulation else self.golden_workflow_histories
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
                description=f"{'simulation' if is_simulation else 'golden'} child {current_path}",
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
