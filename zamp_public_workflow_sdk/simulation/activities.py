"""
Activities for simulation support.

This module contains activities that are used to support simulation functionality,
such as making mocked operations visible in the Temporal UI.
"""

import structlog
from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode
from zamp_public_workflow_sdk.simulation.constants import PayloadKey, DECODED_OUTPUT
from zamp_public_workflow_sdk.simulation.models.mocked_result import MockedResultInput, MockedResultOutput
from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import (
    DecodeNodePayloadInput,
    DecodeNodePayloadOutput,
)

logger = structlog.get_logger(__name__)


@ActionsHub.register_activity("Return mocked result with decoded payloads for simulation")
async def return_mocked_result(input_data: MockedResultInput) -> MockedResultOutput:
    """
    Activity to return mocked results with payload decoding.
    This makes mocked operations visible in Temporal UI.

    This activity:
    1. Checks if payloads need decoding (have "metadata" with "encoding")
    2. Decodes both input and output payloads using decode_node_payload activity in API mode
    3. Returns the decoded output payload wrapped in MockedResultOutput

    Args:
        input_data: The input data containing node_id, encoded_payload dict, and optional action_name

    Returns:
        MockedResultOutput containing the decoded output payload value, or raw output if no decoding needed

    Raises:
        Exception: If decoding fails
    """
    logger.info("Processing mocked result", node_id=input_data.node_id)

    input_payload = input_data.encoded_payload.get(PayloadKey.INPUT_PAYLOAD)
    output_payload = input_data.encoded_payload.get(PayloadKey.OUTPUT_PAYLOAD)

    input_needs_decoding = (
        input_payload
        and isinstance(input_payload, dict)
        and input_payload.get("metadata", {}).get("encoding") is not None
    )
    output_needs_decoding = (
        output_payload
        and isinstance(output_payload, dict)
        and output_payload.get("metadata", {}).get("encoding") is not None
    )

    if not input_needs_decoding and not output_needs_decoding:
        logger.info("No decoding needed, returning raw output", node_id=input_data.node_id)
        return MockedResultOutput(output=output_payload)

    try:
        decoded_payload: DecodeNodePayloadOutput = await ActionsHub.execute_activity(
            "decode_node_payload",
            DecodeNodePayloadInput(
                node_id=input_data.node_id,
                encoded_payload=input_data.encoded_payload,
            ),
            return_type=DecodeNodePayloadOutput,
            execution_mode=ExecutionMode.API,
        )

        logger.info("Successfully decoded mocked result", node_id=input_data.node_id)
        return MockedResultOutput(output=decoded_payload.result.get(DECODED_OUTPUT))

    except Exception as e:
        logger.error(
            "Failed to decode mocked result payloads",
            node_id=input_data.node_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
