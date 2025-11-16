import base64
import json

import structlog
from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode
from zamp_public_workflow_sdk.simulation.models.mocked_result import MockedResultInput, MockedResultOutput
from zamp_public_workflow_sdk.simulation.models.simulation_s3 import (
    DownloadFromS3Input,
    DownloadFromS3Output,
    GetSimulationDataFromS3Input,
    GetSimulationDataFromS3Output,
    SimulationMemo,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import (
    DecodeNodePayloadInput,
    DecodeNodePayloadOutput,
)
from zamp_public_workflow_sdk.simulation.helper import payload_needs_decoding

logger = structlog.get_logger(__name__)


@ActionsHub.register_activity("Return mocked result with decoded payloads for simulation")
async def return_mocked_result(input_params: MockedResultInput) -> MockedResultOutput:
    """
    Activity to return mocked results with output payload decoding.
    This makes mocked operations visible in Temporal UI.

    This activity:
    1. Checks if output payload needs decoding (has "metadata" with "encoding")
    2. Decodes only the output payload using decode_node_payload activity in API mode
    3. Returns the decoded output payload wrapped in MockedResultOutput

    Args:
        input_params: The input parameters containing node_id, input_payload, output_payload, and optional action_name

    Returns:
        MockedResultOutput containing the decoded output payload value, or raw output if no decoding needed

    Raises:
        Exception: If decoding fails
    """

    logger.info("Processing mocked result", node_id=input_params.node_id)

    output_payload = input_params.output_payload

    output_needs_decoding = False
    if output_payload:
        if isinstance(output_payload, list):
            output_needs_decoding = any(payload_needs_decoding(item) for item in output_payload)
        else:
            output_needs_decoding = payload_needs_decoding(output_payload)

    if not output_needs_decoding:
        logger.info("No output decoding needed, returning raw output", node_id=input_params.node_id)
        return MockedResultOutput(root=output_payload)

    try:
        decoded_payload: DecodeNodePayloadOutput = await ActionsHub.execute_activity(
            "decode_node_payload",
            DecodeNodePayloadInput(
                node_id=input_params.node_id,
                input_payload=None,
                output_payload=input_params.output_payload,
            ),
            return_type=DecodeNodePayloadOutput,
            execution_mode=ExecutionMode.API,
        )

        logger.info("Successfully decoded mocked result output", node_id=input_params.node_id)
        return MockedResultOutput(root=decoded_payload.decoded_output)

    except Exception as e:
        logger.error(
            "Failed to decode mocked result output payload",
            node_id=input_params.node_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


@ActionsHub.register_activity("Get simulation data from S3, download and decode it")
async def get_simulation_data_from_s3(
    input_params: GetSimulationDataFromS3Input,
) -> GetSimulationDataFromS3Output:
    """
    Activity to download simulation data from S3 and decode it.

    This activity:
    1. Downloads the simulation data file from S3
    2. Decodes the base64 content
    3. Parses the JSON data
    4. Returns a SimulationMemo model

    Args:
        input_params: Contains the S3 key where simulation data is stored

    Returns:
        GetSimulationDataFromS3Output containing the decoded SimulationMemo

    Raises:
        Exception: If download or decoding fails
    """

    try:
        download_result: DownloadFromS3Output = await ActionsHub.execute_activity(
            "download_from_s3",
            DownloadFromS3Input(
                bucket_name=input_params.bucket_name,
                file_name=input_params.simulation_s3_key,
            ),
            return_type=DownloadFromS3Output,
            execution_mode=ExecutionMode.API,
            skip_simulation=True,
        )

        content_base64 = download_result.content_base64
        decoded_content = base64.b64decode(content_base64).decode()
        simulation_data = json.loads(decoded_content)
        simulation_memo = SimulationMemo.model_validate(simulation_data)

        return GetSimulationDataFromS3Output(simulation_memo=simulation_memo)

    except Exception as e:
        logger.error(
            "Failed to get simulation data from S3",
            simulation_s3_key=input_params.simulation_s3_key,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise Exception(f"Failed to get simulation data from S3: {str(e)}")
