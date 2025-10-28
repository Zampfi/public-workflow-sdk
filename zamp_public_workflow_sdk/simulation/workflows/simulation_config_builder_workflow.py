import temporalio.workflow as workflow

with workflow.unsafe.imports_passed_through():
    import structlog

    from zamp_public_workflow_sdk.actions_hub import ActionsHub
    from zamp_public_workflow_sdk.temporal.workflow_history.models import (
        FetchTemporalWorkflowHistoryInput,
        FetchTemporalWorkflowHistoryOutput,
        WorkflowHistory,
    )
    from zamp_public_workflow_sdk.temporal.workflow_history.constants import EventType, EventField
    from zamp_public_workflow_sdk.simulation.models import (
        SimulationConfig,
        NodeMockConfig,
        NodeStrategy,
        SimulationStrategyConfig,
        TemporalHistoryConfig,
        StrategyType,
    )

    from zamp_public_workflow_sdk.simulation.models.simulation_config_builder import (
        SimulationConfigBuilderInput,
        SimulationConfigBuilderOutput,
    )
    from zamp_public_workflow_sdk.simulation.constants.versions import SupportedVersions

logger = structlog.get_logger(__name__)


@ActionsHub.register_workflow_defn(
    "Workflow that generates simulation config by extracting all node IDs from a workflow",
    labels=["temporal", "simulation"],
)
class SimulationConfigBuilderWorkflow:
    """Generate simulation config by extracting mockable node IDs from workflow execution history."""

    MAIN_WORKFLOW_KEY = "main-workflow"

    def __init__(self):
        """Initialize with workflow history cache and skip list."""
        self.workflow_histories: dict[str, WorkflowHistory] = {}
        self.nodes_to_skip = [
            "generate_llm_model_response",
            "generate_embeddings",
            "generate_with_template",
            "extract_ocr_data",
            "fetch_from_responses_api",
        ]

    @ActionsHub.register_workflow_run
    async def execute(self, input: SimulationConfigBuilderInput) -> SimulationConfigBuilderOutput:
        """Extract all mockable node IDs from workflow and generate simulation config."""
        if input.execute_actions:
            self.nodes_to_skip.extend(input.execute_actions)
        logger.info("Starting simulation config generation", workflow_id=input.workflow_id, run_id=input.run_id)

        main_history = await self._fetch_workflow_history(input.workflow_id, input.run_id)
        self.workflow_histories[self.MAIN_WORKFLOW_KEY] = main_history

        # Extract all node IDs recursively
        all_node_ids = await self._extract_node_ids(main_history)
        logger.info("Extracted node IDs", total_nodes=len(all_node_ids))

        # Generate and return simulation config
        simulation_config = self._generate_simulation_config(all_node_ids, input.workflow_id, input.run_id)
        return SimulationConfigBuilderOutput(simulation_config=simulation_config)

    def _node_has_event(self, node_data, event_types: list[str]) -> bool:
        """Check if node has any of the specified event types."""
        for event in node_data.node_events:
            event_type = event.get(EventField.EVENT_TYPE.value)
            if event_type in event_types:
                return True
        return False

    def _is_child_workflow(self, node_data) -> bool:
        """Check if node is a child workflow."""
        return self._node_has_event(
            node_data,
            [
                EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED.value,
                EventType.CHILD_WORKFLOW_EXECUTION_STARTED.value,
                EventType.WORKFLOW_EXECUTION_STARTED.value,
            ],
        )

    def _is_workflow_execution(self, node_data) -> bool:
        """Check if node is workflow execution itself (should be filtered)."""
        return self._node_has_event(node_data, [EventType.WORKFLOW_EXECUTION_STARTED.value])

    def _is_mockable(self, node_id: str) -> bool:
        """Check if node is mockable (not in skip list)."""
        is_mockable = not any(skip_pattern in node_id for skip_pattern in self.nodes_to_skip)
        if is_mockable:
            logger.info("Including activity node", node_id=node_id)
        else:
            logger.info("Skipping node (in skip list)", node_id=node_id)
        return is_mockable

    def _can_mock_as_single_node(self, nodes_data: dict) -> bool:
        """Check if child workflow can be mocked as single node.

        Returns True if:
        - All activities are mockable
        - No nested child workflows
        """
        for node_id, node_data in nodes_data.items():
            if self._is_workflow_execution(node_data):
                continue

            if self._is_child_workflow(node_data):
                return False

            if not self._is_mockable(node_id):
                return False

        return True

    async def _process_child_workflow(self, node_id: str, workflow_history: WorkflowHistory) -> list[str]:
        """Process child workflow and return node IDs to mock.

        Returns [child_workflow_node_id] if can mock as single node, else recursively extracts node IDs.
        """
        logger.info("Processing child workflow", node_id=node_id)

        try:
            child_workflow_id, child_run_id = workflow_history.get_child_workflow_workflow_id_run_id(node_id)
            child_history = await self._fetch_workflow_history(child_workflow_id, child_run_id)
            nodes_data = child_history.get_nodes_data()

            if self._can_mock_as_single_node(nodes_data):
                logger.info("Mocking as single node", node_id=node_id)
                return [node_id]

            logger.info("Extracting recursively", node_id=node_id)
            return await self._extract_node_ids(child_history)

        except Exception as e:
            logger.error("Failed to process child workflow", node_id=node_id, error=str(e))
            raise

    async def _process_node(self, node_id: str, node_data, workflow_history: WorkflowHistory) -> list[str]:
        """Process single node and return node IDs to include."""
        if self._is_workflow_execution(node_data):
            logger.info("Skipping workflow execution node", node_id=node_id)
            return []

        if self._is_child_workflow(node_data):
            return await self._process_child_workflow(node_id, workflow_history)

        if self._is_mockable(node_id):
            return [node_id]

        return []

    async def _extract_node_ids(self, workflow_history: WorkflowHistory) -> list[str]:
        """Extract all mockable node IDs from workflow recursively."""
        nodes_data = workflow_history.get_nodes_data()
        logger.info("Processing workflow nodes", node_count=len(nodes_data))

        all_node_ids = []
        for node_id, node_data in nodes_data.items():
            node_ids = await self._process_node(node_id, node_data, workflow_history)
            all_node_ids.extend(node_ids)

        return all_node_ids

    async def _fetch_workflow_history(self, workflow_id: str, run_id: str) -> FetchTemporalWorkflowHistoryOutput:
        """Fetch workflow execution history from Temporal."""
        logger.info("Fetching workflow history", workflow_id=workflow_id, run_id=run_id)

        try:
            history = await ActionsHub.execute_child_workflow(
                "FetchTemporalWorkflowHistoryWorkflow",
                FetchTemporalWorkflowHistoryInput(workflow_id=workflow_id, run_id=run_id),
                result_type=FetchTemporalWorkflowHistoryOutput,
            )
            logger.info(
                "Successfully fetched workflow history", workflow_id=workflow_id, events_count=len(history.events)
            )
            return history

        except Exception as e:
            logger.error("Failed to fetch workflow history", workflow_id=workflow_id, error=str(e))
            raise

    def _generate_simulation_config(
        self,
        mocked_node_ids: list[str],
        reference_workflow_id: str,
        reference_run_id: str,
    ) -> SimulationConfig:
        """Generate simulation config with TEMPORAL_HISTORY strategy for all extracted node IDs."""
        strategy = SimulationStrategyConfig(
            type=StrategyType.TEMPORAL_HISTORY,
            config=TemporalHistoryConfig(
                reference_workflow_id=reference_workflow_id,
                reference_workflow_run_id=reference_run_id,
            ),
        )

        return SimulationConfig(
            version=SupportedVersions.V1_0_0.value,
            mock_config=NodeMockConfig(node_strategies=[NodeStrategy(strategy=strategy, nodes=mocked_node_ids)]),
        )
