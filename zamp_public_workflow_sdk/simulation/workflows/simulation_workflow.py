from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import structlog
    from typing import Any, Dict, List
    from zamp_public_workflow_sdk.actions_hub import ActionsHub
    from zamp_public_workflow_sdk.simulation.models.simulation_workflow import (
        NodePayloadResult,
        SimulationWorkflowOutput,
        SimulationWorkflowInput,
        NodePayloadType,
    )
    from zamp_public_workflow_sdk.simulation.helper import (
        MAIN_WORKFLOW_IDENTIFIER,
        extract_node_payload,
        fetch_temporal_history,
    )
    from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import (
        DecodeNodePayloadInput,
        DecodeNodePayloadOutput,
    )
    from zamp_public_workflow_sdk.simulation.constants import (
        NEEDS_CHILD_TRAVERSAL,
    )

logger = structlog.get_logger(__name__)


@ActionsHub.register_workflow_defn(
    "Wrapper workflow that executes workflows in simulation mode and extracts activity data",
    labels=["core", "simulation"],
)
class SimulationWorkflow:
    """
    Wrapper workflow for executing workflows with simulation and activity payload extraction.

    This workflow:
    1. Resolves the target workflow class from workflow name
    2. Executes the workflow as a child workflow with simulation_config
    4. Fetches workflow history from Temporal API (not S3)
    5. Traverses into child workflow executions recursively
    6. Parses history to extract activity inputs/outputs based on output_schema
    7. Returns structured activity data including payloads from child workflows

    Example usage:
        input = SimulationCodeWorkflowInput(
            original_workflow_name="StripeFetchInvoicesWorkflow",
            original_workflow_params={
                "newer_than": "2024-01-01",
                "zamp_metadata_context": {...}
            },
            simulation_config=SimulationConfig(
                mock_config=NodeMockConfig(...)
            ),
            output_schema=SimulationOutputSchema(
                node_payloads={
                    "gmail_search_messages#1": "INPUT_OUTPUT",
                    "parse_email#3": "OUTPUT"
                }
            ),
        )
        result = await workflow.execute(input)
    """

    @ActionsHub.register_workflow_run
    async def execute(self, input_params: SimulationWorkflowInput) -> SimulationWorkflowOutput:
        """Execute workflow in simulation mode and extract activity data.

        Args:
            input_params: Input parameters including workflow name, params, and output schema

        Returns:
            SimulationWorkflowOutput with workflow result and extracted activity data

        Raises:
            NonRetryableError: If workflow resolution fails
        """

        # Step 1: Prepare workflow parameters with simulation_config
        workflow_params = self._prepare_workflow_params(input_params)
        logger.info("Workflow parameters prepared")

        # Step 3: Execute child workflow
        logger.info(
            "About to execute child workflow",
            workflow_name=input_params.workflow_name,
            workflow_params_keys=list(workflow_params.keys()),
        )

        workflow_result, workflow_id, run_id = await self._execute_child_workflow(
            workflow_class=input_params.workflow_name,
            workflow_params=workflow_params,
            workflow_name=input_params.workflow_name,
        )

        logger.info(
            "Child workflow executed",
            workflow_id=workflow_id,
            run_id=run_id,
            has_result=workflow_result is not None,
        )

        node_payloads = await self._fetch_and_parse_node_payloads(
            workflow_id=workflow_id,
            run_id=run_id,
            node_payloads=input_params.output_schema.node_payloads,
        )

        # Step 5: Return structured output
        result = SimulationWorkflowOutput(node_payloads=node_payloads)

        logger.info(
            "SimulationWorkflow completed successfully",
            workflow_id=workflow_id,
            run_id=run_id,
            payloads_count=len(node_payloads),
        )

        return result

    def _prepare_workflow_params(self, input_params: SimulationWorkflowInput) -> dict[str, Any]:
        """Prepare workflow parameters with simulation_config.

        Args:
            input_params: Input parameters for SimulationCodeWorkflow

        Returns:
            Dictionary of workflow parameters with simulation_config added
        """
        workflow_params = {**input_params.workflow_params}

        workflow_params["simulation_config"] = input_params.simulation_config

        # Add zamp_metadata_context if provided and not already in params
        if input_params.zamp_metadata_context and "zamp_metadata_context" not in workflow_params:
            workflow_params["zamp_metadata_context"] = input_params.zamp_metadata_context

        return workflow_params

    async def _execute_child_workflow(
        self,
        workflow_class: Any,
        workflow_params: dict[str, Any],
        workflow_name: str,
    ) -> tuple[Any, str, str]:
        """Execute child workflow in simulation mode.

        Args:
            workflow_class: The workflow class to execute
            workflow_params: Parameters to pass to the workflow
            workflow_name: Name of the workflow for logging

        Returns:
            Tuple of (workflow_result, workflow_id, run_id)
        """
        logger.info(
            "Executing child workflow",
            workflow_name=workflow_name,
        )

        child_handle: workflow.ChildWorkflowHandle[Any, Any] = await workflow.start_child_workflow(
            workflow_class,
            workflow_params,
            static_summary=f"Simulation: {workflow_name}",
        )
        workflow_id = child_handle.id
        run_id = child_handle.first_execution_run_id

        logger.info(
            "Waiting for child workflow to complete",
            workflow_id=workflow_id,
            run_id=run_id,
            workflow_name=workflow_name,
        )

        workflow_result = await child_handle

        logger.info(
            "Child workflow completed synchronously",
            workflow_id=workflow_id,
            run_id=run_id,
            has_result=workflow_result is not None,
        )
        return workflow_result, workflow_id, run_id

    async def _fetch_and_parse_node_payloads(
        self,
        workflow_id: str,
        run_id: str,
        node_payloads: Dict[str, NodePayloadType],
    ) -> List[NodePayloadResult]:
        """Fetch workflow history and parse node payloads based on output schema.

        Args:
            workflow_id: The workflow ID to fetch history for
            run_id: The run ID to fetch history for
            node_payloads: Dictionary mapping node IDs to payload types

        Returns:
            List of NodePayloadResult objects
        """
        logger.info(
            "Fetching and parsing node payloads",
            workflow_id=workflow_id,
            run_id=run_id,
            node_count=len(node_payloads),
        )

        # Fetch and extract node payloads from workflow history
        encoded_node_payloads = await self._fetch_node_payloads(workflow_id, run_id, list(node_payloads.keys()))

        # Process each node payload
        result: List[NodePayloadResult] = []
        for node_id, payload_type in node_payloads.items():
            payload_result = await self._process_node_payload(node_id, payload_type, encoded_node_payloads)
            result.append(payload_result)

        logger.info(
            "Completed fetching and parsing node payloads",
            workflow_id=workflow_id,
            run_id=run_id,
            payloads_count=len(result),
        )
        return result

    async def _fetch_node_payloads(self, workflow_id: str, run_id: str, node_ids: list[str]) -> dict[str, Any]:
        """Fetch temporal history and extract node payloads.

        Args:
            workflow_id: The workflow ID
            run_id: The run ID
            node_ids: List of node IDs to extract

        Returns:
            Dictionary mapping node IDs to encoded payloads

        Raises:
            Exception: If fetch or extraction fails
        """
        try:
            temporal_history = await fetch_temporal_history(
                node_ids=node_ids,
                workflow_id=workflow_id,
                run_id=run_id,
            )
            if temporal_history is None:
                raise Exception(
                    f"Failed to fetch temporal history for workflow_id={workflow_id}, run_id={run_id}: returned None"
                )
        except Exception as e:
            logger.error(
                "Failed to fetch temporal history",
                workflow_id=workflow_id,
                run_id=run_id,
                error=str(e),
            )
            raise Exception(f"Failed to fetch temporal history for workflow_id={workflow_id}, run_id={run_id}") from e

        try:
            node_payloads = await extract_node_payload(
                node_ids=node_ids,
                workflow_histories_map={MAIN_WORKFLOW_IDENTIFIER: temporal_history},
            )
            logger.info("Extracted node payloads", node_count=len(node_payloads))
            return node_payloads
        except Exception as e:
            logger.error(
                "Failed to extract node payloads",
                workflow_id=workflow_id,
                error=str(e),
            )
            raise Exception(f"Failed to extract node payloads for workflow_id={workflow_id}, run_id={run_id}") from e

    async def _process_node_payload(
        self,
        node_id: str,
        payload_type: NodePayloadType,
        node_payloads: dict[str, Any],
    ) -> NodePayloadResult:
        """Process a single node payload: traverse child if needed, decode, and build result.

        Args:
            node_id: The node ID to process
            payload_type: The payload type (INPUT, OUTPUT, or INPUT_OUTPUT)
            node_payloads: Dictionary of all node payloads

        Returns:
            NodePayloadResult with decoded input/output based on payload type
        """
        logger.info("Processing node payload", node_id=node_id, payload_type=payload_type)

        # Get encoded payload
        encoded_payload = node_payloads.get(node_id)
        if not encoded_payload:
            logger.warning("No encoded payload found for node", node_id=node_id)
            return NodePayloadResult(node_id=node_id, input=None, output=None)

        # Traverse child workflow if needed
        encoded_payload = await self._traverse_child_workflow_if_needed(node_id, encoded_payload)

        # Decode payload - returns DecodeNodePayloadOutput or None
        decoded_output = await self._decode_node_payload(node_id, encoded_payload)
        if not decoded_output:
            return NodePayloadResult(node_id=node_id, input=None, output=None)

        # Build result based on payload type
        return self._build_payload_result(node_id, payload_type, decoded_output)

    async def _traverse_child_workflow_if_needed(self, node_id: str, encoded_payload: dict[str, Any]) -> dict[str, Any]:
        """Traverse into child workflow if the node needs it and return child's main node payload.

        Args:
            node_id: The parent node ID
            encoded_payload: The encoded payload which may contain traversal metadata

        Returns:
            The child workflow's main node payload if traversal needed, otherwise original payload
        """
        # Check if traversal is needed
        if not isinstance(encoded_payload, dict) or not encoded_payload.get(NEEDS_CHILD_TRAVERSAL):
            return encoded_payload

        child_workflow_id = encoded_payload.get("child_workflow_id")
        child_run_id = encoded_payload.get("child_run_id")

        if not child_workflow_id or not child_run_id:
            return encoded_payload

        logger.info(
            "Child workflow needs traversal",
            node_id=node_id,
            child_workflow_id=child_workflow_id,
        )

        try:
            # Fetch child workflow history and extract main node payload
            child_history = await fetch_temporal_history(
                node_ids=[node_id],
                workflow_id=child_workflow_id,
                run_id=child_run_id,
            )

            child_payloads = child_history.get_nodes_data_encoded(target_node_ids=None)
            logger.info(
                "Child workflow payloads extracted",
                node_id=node_id,
                child_payloads_count=len(child_payloads),
            )

            child_main_node = self._find_main_workflow_node(child_payloads, node_id)

            if child_main_node:
                logger.info("Successfully extracted child workflow output", node_id=node_id)
                return child_main_node

            logger.warning("No main workflow node found in child history", node_id=node_id)

        except Exception as e:
            logger.error(
                "Failed to fetch child workflow history",
                node_id=node_id,
                error=str(e),
            )

        return encoded_payload

    @staticmethod
    def _find_main_workflow_node(child_payloads: dict[str, Any], parent_node_id: str) -> dict[str, Any] | None:
        """Find the main workflow node in child payloads (node without '.' separator).

        Args:
            child_payloads: Dictionary of child workflow payloads
            parent_node_id: Parent node ID for logging

        Returns:
            The main workflow node payload or None if not found
        """
        for child_node_id, child_payload in child_payloads.items():
            if "." not in child_node_id:
                logger.info(
                    "Found main workflow node in child",
                    parent_node_id=parent_node_id,
                    child_node_id=child_node_id,
                )
                return child_payload
        return None

    async def _decode_node_payload(self, node_id: str, encoded_payload: dict[str, Any]) -> DecodeNodePayloadOutput | None:
        """Decode node payload using decode_node_payload activity.

        Args:
            node_id: The node ID
            encoded_payload: Dict containing 'input_payload' and 'output_payload' keys

        Returns:
            Decoded payload result or None if decoding fails
        """
        try:
            decoded_data = await ActionsHub.execute_activity(
                "decode_node_payload",
                DecodeNodePayloadInput(
                    node_id=node_id,
                    input_payload=encoded_payload.get("input_payload"),
                    output_payload=encoded_payload.get("output_payload"),
                ),
                summary=f"{node_id}",
                return_type=DecodeNodePayloadOutput,
            )
            logger.info(
                "Successfully decoded node payload",
                node_id=node_id,
                has_input=decoded_data.decoded_input is not None,
                has_output=decoded_data.decoded_output is not None,
            )
            return decoded_data
        except Exception as e:
            logger.error("Failed to decode node payload", node_id=node_id, error=str(e))
            return None

    @staticmethod
    def _build_payload_result(
        node_id: str, payload_type: NodePayloadType, decoded_data: DecodeNodePayloadOutput
    ) -> NodePayloadResult:
        """Build NodePayloadResult based on payload type.

        Args:
            node_id: The node ID
            payload_type: The payload type (INPUT, OUTPUT, or INPUT_OUTPUT)
            decoded_data: The decoded payload data output

        Returns:
            NodePayloadResult with appropriate input/output based on payload type
        """
        decoded_input = None
        decoded_output = None

        if payload_type in [NodePayloadType.INPUT, NodePayloadType.INPUT_OUTPUT]:
            decoded_input = decoded_data.decoded_input

        if payload_type in [NodePayloadType.OUTPUT, NodePayloadType.INPUT_OUTPUT]:
            decoded_output = decoded_data.decoded_output

        return NodePayloadResult(
            node_id=node_id,
            input=decoded_input,
            output=decoded_output,
        )
