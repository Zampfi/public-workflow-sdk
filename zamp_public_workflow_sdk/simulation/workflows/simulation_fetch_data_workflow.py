from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import base64
    import json
    import structlog
    from datetime import timedelta

    from zamp_public_workflow_sdk.actions_hub import ActionsHub
    from zamp_public_workflow_sdk.actions_hub.constants import get_simulation_s3_key
    from zamp_public_workflow_sdk.simulation.constants.simulation import SIMULATION_S3_BUCKET
    from zamp_public_workflow_sdk.simulation.models.simulation_fetch_data_workflow import (
        SimulationFetchDataWorkflowInput,
        SimulationFetchDataWorkflowOutput,
    )
    from zamp_public_workflow_sdk.simulation.models.simulation_s3 import UploadToS3Input

    logger = structlog.get_logger(__name__)


@ActionsHub.register_workflow_defn(
    "Workflow that fetches simulation data using strategy pattern",
    labels=["simulation", "strategy"],
)
class SimulationFetchDataWorkflow:
    def __init__(self):
        pass

    @ActionsHub.register_workflow_run
    async def execute(self, input: SimulationFetchDataWorkflowInput) -> SimulationFetchDataWorkflowOutput:
        """
        Execute the simulation data workflow to fetch and process workflow history.

        Args:
            input: Contains simulation configuration with node strategies and workflow_id

        Returns:
            Mapping of node IDs to their response data and S3 key where data is stored
        """
        from zamp_public_workflow_sdk.simulation.workflow_simulation_service import (
            WorkflowSimulationService,
        )

        node_id_to_payload_map = {}

        for node_strategy in input.simulation_config.mock_config.node_strategies:
            strategy = WorkflowSimulationService.get_strategy(node_strategy)
            if strategy is None:
                logger.error(
                    "Strategy not found for node",
                    node_ids=node_strategy.nodes,
                    strategy_type=node_strategy.strategy.type,
                )
                continue
            try:
                result = await strategy.execute(
                    node_ids=node_strategy.nodes,
                )
                node_id_to_payload_map.update(result.node_id_to_payload_map)
            except Exception as e:
                logger.error(
                    "Error processing node with strategy",
                    node_ids=node_strategy.nodes,
                    strategy_type=node_strategy.strategy.type,
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Upload simulation data to S3
        s3_key = None
        try:
            s3_key = get_simulation_s3_key(input.workflow_id)
            simulation_data = {
                "config": input.simulation_config.model_dump(),
                "node_id_to_payload_map": {
                    node_id: payload.model_dump() if hasattr(payload, "model_dump") else payload
                    for node_id, payload in node_id_to_payload_map.items()
                },
            }
            blob_base64 = base64.b64encode(json.dumps(simulation_data).encode()).decode()

            await ActionsHub.execute_activity(
                "upload_to_s3",
                UploadToS3Input(
                    bucket_name=SIMULATION_S3_BUCKET,
                    file_name=s3_key,
                    blob_base64=blob_base64,
                    content_type="application/json",
                ),
                start_to_close_timeout=timedelta(seconds=30),
                skip_simulation=True,
            )
            logger.info("Simulation data uploaded to S3", s3_key=s3_key)
        except Exception as e:
            logger.error(
                "Failed to upload simulation data to S3",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Continue without S3 upload - s3_key will be None

        return SimulationFetchDataWorkflowOutput(node_id_to_payload_map=node_id_to_payload_map, s3_key=s3_key)
