from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import structlog
    from typing import Any
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
    from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload


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
    4. Fetches workflow history from s3 if not available, otherwise from temporal API
    5. Traverses into child workflow executions recursively
    6. Parses history to extract activity inputs/outputs based on output_schema
    7. Returns structured activity data including payloads from child workflows

    Example usage:
        input = SimulationWorkflowInput(
            workflow_name="StripeFetchInvoicesWorkflow",
            workflow_params={
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

        workflow_params = self._prepare_workflow_params(input_params)

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
            input_params: Input parameters for SimulationWorkflow

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

        child_handle: workflow.ChildWorkflowHandle[Any, Any] = await ActionsHub.start_child_workflow(
            workflow_class,
            workflow_params,
            static_summary=f"Simulation: {workflow_name}",
            skip_node_id_gen=True,
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
        node_payloads: dict[str, NodePayloadType],
    ) -> list[NodePayloadResult]:
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
        encoded_node_payloads = await self._fetch_node_payloads(
            workflow_id=workflow_id, run_id=run_id, node_ids=list(node_payloads.keys())
        )

        # Process each node payload
        result: list[NodePayloadResult] = []
        for node_id, payload_type in node_payloads.items():
            payload_result = await self._process_node_payload(
                node_id=node_id, payload_type=payload_type, node_payloads=encoded_node_payloads
            )
            result.append(payload_result)
            
        return result

    async def _fetch_node_payloads(self, workflow_id: str, run_id: str, node_ids: list[str]) -> dict[str, NodePayload]:
        """Fetch temporal history and extract node payloads.

        Args:
            workflow_id: The workflow ID
            run_id: The run ID
            node_ids: List of node IDs to extract

        Returns:
            Dictionary mapping node IDs to NodePayload instances with encoded data

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
        node_payloads: dict[str, NodePayload],
    ) -> NodePayloadResult:
        """Process a single node payload: traverse child if needed, decode, and build result.

        Args:
            node_id: The node ID to process
            payload_type: The payload type (INPUT, OUTPUT, or INPUT_OUTPUT)
            node_payloads: Dictionary mapping node IDs to NodePayload instances

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
        encoded_payload = await self._traverse_child_workflow_if_needed(
            node_id=node_id, encoded_payload=encoded_payload
        )

        # Decode only what's needed based on payload_type
        decoded_output = await self._decode_node_payload(
            node_id=node_id, encoded_payload=encoded_payload, payload_type=payload_type
        )
        if not decoded_output:
            return NodePayloadResult(node_id=node_id, input=None, output=None)

        # Build result based on payload type
        return self._build_payload_result(node_id=node_id, payload_type=payload_type, decoded_data=decoded_output)

    async def _traverse_child_workflow_if_needed(self, node_id: str, encoded_payload: NodePayload) -> NodePayload:
        """Traverse into child workflow if the node needs it and return child's main node payload.

        Args:
            node_id: The parent node ID
            encoded_payload: The NodePayload instance which may contain traversal metadata

        Returns:
            The child workflow's main node NodePayload if traversal needed, otherwise original payload
        """
        # Check if traversal is needed
        if not encoded_payload.needs_child_traversal:
            return encoded_payload

        child_workflow_id = encoded_payload.child_workflow_id
        child_run_id = encoded_payload.child_run_id

        if not child_workflow_id or not child_run_id:
            return encoded_payload

        logger.info(
            "Traversing child workflow",
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

            child_main_node = self._find_main_workflow_node(child_payloads=child_payloads, node_id=node_id)

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

    def _find_main_workflow_node(self, child_payloads: dict[str, NodePayload], node_id: str) -> NodePayload | None:
        """Find the main workflow node in child payloads.

        The main workflow node is the full workflow path that contains the activity.
        This is everything before the last segment (the activity name).

        Examples:
            - node_id="EnhancedStripeInvoiceProcessingWorkflow#1.query_data#1"
              -> extracts "EnhancedStripeInvoiceProcessingWorkflow#1" and searches for it in child_payloads
            - node_id="EnhancedStripeInvoiceProcessingWorkflow#1.POBackedInvoiceProcessingWorkflow#1.emit_custom_log#1"
              -> extracts "EnhancedStripeInvoiceProcessingWorkflow#1.POBackedInvoiceProcessingWorkflow#1" and searches for it in child_payloads
            - node_id="Parent#1.Child#1.GrandChild#1.activity#1"
              -> extracts "Parent#1.Child#1.GrandChild#1" and searches for it in child_payloads

        Args:
            child_payloads: Dictionary mapping node IDs to NodePayload instances
            node_id: Node ID (full path including activity)

        Returns:
            The main workflow NodePayload or None if not found
        """
        parts = node_id.split(".")
        target_workflow_path = ".".join(parts[:-1]) if len(parts) > 1 else parts[0]

        if target_workflow_path in child_payloads:
            return child_payloads[target_workflow_path]

        for child_node_id, child_payload in child_payloads.items():
            if child_node_id.startswith(target_workflow_path + "."):
                return child_payload

        return None

    async def _decode_node_payload(
        self, node_id: str, encoded_payload: NodePayload, payload_type: NodePayloadType
    ) -> DecodeNodePayloadOutput | None:
        """Decode node payload using decode_node_payload activity.

        Only decodes the payloads needed based on payload_type to optimize performance.

        Args:
            node_id: The node ID
            encoded_payload: NodePayload instance containing input_payload and output_payload
            payload_type: The payload type (INPUT, OUTPUT, or INPUT_OUTPUT)

        Returns:
            Decoded payload result or None if decoding fails
        """
        try:
            # Determine what to decode based on payload_type
            input_to_decode = None
            output_to_decode = None

            if payload_type in [NodePayloadType.INPUT, NodePayloadType.INPUT_OUTPUT]:
                input_to_decode = encoded_payload.input_payload

            if payload_type in [NodePayloadType.OUTPUT, NodePayloadType.INPUT_OUTPUT]:
                output_to_decode = encoded_payload.output_payload

            decoded_data = await ActionsHub.execute_activity(
                "decode_node_payload",
                DecodeNodePayloadInput(
                    node_id=node_id,
                    input_payload=input_to_decode,
                    output_payload=output_to_decode,
                ),
                summary=f"{node_id}",
                return_type=DecodeNodePayloadOutput,
            )
            logger.info(
                "Successfully decoded node payload",
                node_id=node_id,
                payload_type=payload_type.value,
                has_input=decoded_data.decoded_input is not None,
                has_output=decoded_data.decoded_output is not None,
            )
            return decoded_data
        except Exception as e:
            logger.error("Failed to decode node payload", node_id=node_id, error=str(e))
            return None

    def _build_payload_result(
        self, node_id: str, payload_type: NodePayloadType, decoded_data: DecodeNodePayloadOutput
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
