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
    """Workflow for generating simulation configuration from workflow histories.

    This workflow extracts all node IDs from a workflow execution history,
    including nodes from child workflows, and generates a simulation configuration
    that can be used to mock those nodes during simulation runs.

    The extraction process:
    1. Fetches the main workflow history
    2. Recursively processes all nodes, identifying child workflows
    3. Extracts node IDs from child workflows by fetching their histories
    4. Applies skip filters to exclude unwanted nodes
    5. Generates a simulation configuration with all collected node IDs
    """

    MAIN_WORKFLOW_KEY = "main-workflow"

    def __init__(self):
        """Initialize the simulation config builder workflow.

        Sets up internal caches and configuration for processing workflow histories
        and extracting node IDs for simulation configuration generation.
        """
        self.workflow_histories: dict[str, WorkflowHistory] = {}
        # List of node IDs to skip
        self.nodes_to_skip = [
            "generate_llm_model_response",
            "generate_embeddings",
            "generate_with_template",
            "extract_ocr_data",
            "fetch_from_responses_api",
            "ChainOfThoughtWorkflow",
        ]

    @ActionsHub.register_workflow_run
    async def execute(self, input: SimulationConfigBuilderInput) -> SimulationConfigBuilderOutput:
        """Execute the simulation configuration generation workflow.

        Processes the specified workflow execution to extract all node IDs
        and generate a comprehensive simulation configuration.

        Args:
            input: Configuration input containing workflow_id and run_id

        Returns:
            SimulationConfigBuilderOutput containing the generated simulation config

        Raises:
            Exception: If workflow history cannot be fetched or processed
        """
        if input.execute_actions:
            self.nodes_to_skip.extend(input.execute_actions)
        logger.info(
            "Starting GenerateSimulationConfigWorkflow",
            workflow_id=input.workflow_id,
            run_id=input.run_id,
        )

        # Step 1: Fetch main workflow history
        main_history = await self._fetch_workflow_history(
            workflow_id=input.workflow_id,
            run_id=input.run_id,
        )
        self.workflow_histories[self.MAIN_WORKFLOW_KEY] = main_history

        # Step 2: Extract all node IDs recursively
        all_node_ids = await self._extract_all_node_ids_recursively(
            workflow_history=main_history,
        )

        logger.info(
            "Extracted all node IDs",
            total_nodes=len(all_node_ids),
        )

        # Step 3: Generate simulation config
        simulation_config = self._generate_simulation_config(
            mocked_node_ids=all_node_ids,
            reference_workflow_id=input.workflow_id,
            reference_run_id=input.run_id,
        )

        return SimulationConfigBuilderOutput(
            simulation_config=simulation_config,
        )

    def _is_child_workflow_node(self, node_data) -> bool:
        """Determine if a node represents a child workflow execution.

        Examines the node's events to identify if it contains child workflow
        execution events, indicating this node spawns a child workflow.

        Args:
            node_data: Node data containing workflow events

        Returns:
            True if the node contains child workflow events, False otherwise
        """
        for event in node_data.node_events:
            event_type = event.get(EventField.EVENT_TYPE.value)
            if event_type in [
                EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED.value,
                EventType.CHILD_WORKFLOW_EXECUTION_STARTED.value,
            ]:
                return True
        return False

    def _is_workflow_execution_node(self, node_data) -> bool:
        """Determine if a node represents the workflow execution itself (not an activity or child workflow).

        These nodes should be filtered out when extracting node IDs.

        Args:
            node_data: Node data containing workflow events

        Returns:
            True if the node represents workflow execution, False otherwise
        """
        for event in node_data.node_events:
            event_type = event.get(EventField.EVENT_TYPE.value)
            if event_type == EventType.WORKFLOW_EXECUTION_STARTED.value:
                return True
        return False

    async def _process_child_workflow_node(self, node_id: str, workflow_history: WorkflowHistory) -> list[str]:
        """Process a child workflow node and extract its node IDs.

        Fetches the child workflow's execution history and recursively extracts
        all node IDs from it. If ALL activities within the child workflow would
        be mocked (none are in skip list), returns just the child workflow node_id.
        Otherwise, returns individual activity node IDs.

        Args:
            node_id: The node ID that represents the child workflow
            workflow_history: The parent workflow history containing the child workflow

        Returns:
            List containing either:
            - Just the child workflow node_id if all activities would be mocked
            - Individual activity node IDs if some activities would be skipped

        Note:
            Returns an empty list if child workflow processing fails
        """
        logger.info(
            "Found child workflow node - skipping and traversing",
            node_id=node_id,
        )

        try:
            child_workflow_id, child_run_id = workflow_history.get_child_workflow_workflow_id_run_id(node_id=node_id)

            logger.info(
                "Fetching child workflow history",
                child_node_id=node_id,
                child_workflow_id=child_workflow_id,
                child_run_id=child_run_id,
            )

            # Fetch child workflow history
            child_history = await self._fetch_workflow_history(
                workflow_id=child_workflow_id,
                run_id=child_run_id,
            )

            # Get all nodes from child workflow (activities + nested child workflows)
            nodes_data = child_history.get_nodes_data()

            # Check if there are any nested child workflows and if all activities are mockable
            has_nested_child_workflows = False
            all_activities_mockable = True

            for child_node_id, child_node_data in nodes_data.items():
                if self._is_workflow_execution_node(child_node_data):
                    continue
                if self._is_child_workflow_node(child_node_data):
                    has_nested_child_workflows = True
                else:
                    if not self._should_include_node(node_id=child_node_id):
                        all_activities_mockable = False

            # Only return child workflow node_id if:
            # 1. All activities are mockable
            # 2. There are NO nested child workflows
            # 3. The child workflow node_id itself is not in the skip list
            if all_activities_mockable and not has_nested_child_workflows and len(nodes_data) > 0:
                if self._should_include_node(node_id=node_id):
                    logger.info(
                        "All activities in child workflow would be mocked - mocking entire child workflow",
                        child_node_id=node_id,
                        total_nodes=len(nodes_data),
                    )
                    return [node_id]  # Return the child workflow node_id itself

            # Either has nested child workflows or some activities not mockable - recursively extract
            logger.info(
                "Some activities in child workflow would be skipped - mocking individual activities",
                child_node_id=node_id,
                has_nested_child_workflows=has_nested_child_workflows,
                all_activities_mockable=all_activities_mockable,
            )
            return await self._extract_all_node_ids_recursively(workflow_history=child_history)

        except Exception as e:
            logger.error(
                "Failed to extract child workflow nodes",
                node_id=node_id,
                error=str(e),
            )
            raise

    def _should_include_node(self, node_id: str) -> str | None:
        """Determine if a node should be included in the simulation configuration.

        Applies filtering logic to determine whether a node should be included
        in the final simulation configuration based on skip patterns.

        Args:
            node_id: The node ID to evaluate for inclusion

        Returns:
            The node ID if it should be included, None if it should be skipped
        """
        # Check if this node should be skipped based on the skip list
        if any(skip_pattern in node_id for skip_pattern in self.nodes_to_skip):
            logger.info(
                "Skipping node (in skip list)",
                node_id=node_id,
            )
            return None
        else:
            logger.info(
                "Adding activity node",
                node_id=node_id,
            )
            return node_id

    async def _extract_all_node_ids_recursively(self, workflow_history: WorkflowHistory) -> list[str]:
        """Extract all node IDs from a workflow and its child workflows.

        Recursively processes a workflow history to extract all node IDs,
        including those from child workflows. Applies filtering to exclude
        unwanted nodes based on configured skip patterns.

        Args:
            workflow_history: The workflow history to process

        Returns:
            List of all node IDs extracted from the workflow and its children
        """
        all_node_ids = []

        # Get all nodes from current workflow
        nodes_data = workflow_history.get_nodes_data()

        logger.info(
            "Processing workflow nodes",
            node_count=len(nodes_data),
        )

        for node_id, node_data in nodes_data.items():
            # Skip workflow execution nodes (these represent the workflow itself, not activities)
            if self._is_workflow_execution_node(node_data):
                logger.info(
                    "Skipping workflow execution node",
                    node_id=node_id,
                )
                continue

            # Check if this node is a child workflow
            is_child_workflow = self._is_child_workflow_node(node_data=node_data)

            logger.info(
                "Checking node",
                node_id=node_id,
                is_child_workflow=is_child_workflow,
            )

            if is_child_workflow:
                # Process child workflow node
                child_node_ids = await self._process_child_workflow_node(
                    node_id=node_id, workflow_history=workflow_history
                )
                all_node_ids.extend(child_node_ids)
            else:
                # Process node if it should be included
                node_id_to_include = self._should_include_node(node_id=node_id)
                if node_id_to_include:
                    all_node_ids.append(node_id_to_include)

        return all_node_ids

    async def _fetch_workflow_history(self, workflow_id: str, run_id: str) -> FetchTemporalWorkflowHistoryOutput:
        """Fetch workflow execution history from Temporal.

        Uses the FetchTemporalWorkflowHistoryWorkflow to retrieve the complete
        execution history for a specific workflow run.

        Args:
            workflow_id: The workflow ID to fetch history for
            run_id: The specific run ID to fetch history for

        Returns:
            FetchTemporalWorkflowHistoryOutput containing the workflow history

        Raises:
            Exception: If the workflow history cannot be fetched
        """
        logger.info(
            "Fetching workflow history",
            workflow_id=workflow_id,
            run_id=run_id,
        )

        try:
            history: FetchTemporalWorkflowHistoryOutput = await ActionsHub.execute_child_workflow(
                "FetchTemporalWorkflowHistoryWorkflow",
                FetchTemporalWorkflowHistoryInput(
                    workflow_id=workflow_id,
                    run_id=run_id,
                    decode_payloads=True,
                ),
                result_type=FetchTemporalWorkflowHistoryOutput,
            )

            logger.info(
                "Successfully fetched workflow history",
                workflow_id=workflow_id,
                run_id=run_id,
                events_count=len(history.events),
            )

            return history

        except Exception as e:
            logger.error(
                "Failed to fetch workflow history",
                workflow_id=workflow_id,
                run_id=run_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _generate_simulation_config(
        self,
        mocked_node_ids: list[str],
        reference_workflow_id: str,
        reference_run_id: str,
    ) -> SimulationConfig:
        """Generate a simulation configuration for the extracted node IDs.

        Creates a comprehensive simulation configuration that includes all
        extracted node IDs with a TEMPORAL_HISTORY strategy for mocking.

        Args:
            all_node_ids: Complete list of node IDs to include in simulation
            reference_workflow_id: Workflow ID to use as reference for TEMPORAL_HISTORY
            reference_run_id: Run ID to use as reference for TEMPORAL_HISTORY

        Returns:
            SimulationConfig configured to mock all extracted node IDs
        """
        # Create a single node strategy that mocks all nodes
        node_strategy = NodeStrategy(
            strategy=SimulationStrategyConfig(
                type=StrategyType.TEMPORAL_HISTORY,
                config=TemporalHistoryConfig(
                    reference_workflow_id=reference_workflow_id,
                    reference_workflow_run_id=reference_run_id,
                ),
            ),
            nodes=mocked_node_ids,
        )

        mock_config = NodeMockConfig(node_strategies=[node_strategy])

        simulation_config = SimulationConfig(
            version=SupportedVersions.V1_0_0.value,
            mock_config=mock_config,
        )

        return simulation_config
