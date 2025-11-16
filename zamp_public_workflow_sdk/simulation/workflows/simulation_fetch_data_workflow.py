from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import base64
    import structlog

    from zamp_public_workflow_sdk.actions_hub import ActionsHub
    from zamp_public_workflow_sdk.simulation.constants.simulation import (
        get_simulation_s3_key,
    )
    from zamp_public_workflow_sdk.simulation.models.config import SimulationConfig
    from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload
    from zamp_public_workflow_sdk.simulation.models.simulation_fetch_data_workflow import (
        SimulationFetchDataWorkflowInput,
        SimulationFetchDataWorkflowOutput,
    )
    from zamp_public_workflow_sdk.simulation.models.simulation_s3 import (
        SimulationMemo,
        UploadToS3Input,
        UploadToS3Output,
    )

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

        try:
            s3_key = await self._upload_simulation_data_to_s3(
                workflow_id=input.workflow_id,
                simulation_config=input.simulation_config,
                node_id_to_payload_map=node_id_to_payload_map,
                bucket_name=input.bucket_name,
            )
        except Exception as e:
            logger.error(
                "Failed to upload simulation data to S3",
                error=str(e),
                error_type=type(e).__name__,
                bucket_name=input.bucket_name,
                workflow_id=input.workflow_id,
            )
            raise Exception(f"Failed to upload simulation data to S3: {str(e)}")

        return SimulationFetchDataWorkflowOutput(node_id_to_payload_map=node_id_to_payload_map, s3_key=s3_key)

    async def _upload_simulation_data_to_s3(
        self,
        workflow_id: str,
        simulation_config: SimulationConfig,
        node_id_to_payload_map: dict[str, NodePayload],
        bucket_name: str,
    ) -> str:
        """
        Upload simulation data to S3.

        Args:
            workflow_id: The workflow ID for generating S3 key
            simulation_config: Simulation configuration
            node_id_to_payload_map: Mapping of node IDs to their payloads
            bucket_name: S3 bucket name for storing simulation data

        Returns:
            S3 key where data was uploaded

        Raises:
            Exception: If upload fails
        """
        s3_key = get_simulation_s3_key(workflow_id)
        simulation_memo = SimulationMemo(
            config=simulation_config,
            node_id_to_payload_map=node_id_to_payload_map,
        )

        blob_base64 = base64.b64encode(simulation_memo.model_dump_json().encode()).decode()
        result: UploadToS3Output = await ActionsHub.execute_activity(
            "upload_to_s3",
            UploadToS3Input(
                bucket_name=bucket_name,
                file_name=s3_key,
                blob_base64=blob_base64,
                content_type="application/json",
            ),
            return_type=UploadToS3Output,
            skip_simulation=True,
        )
        if not result.s3_url:
            raise Exception(f"Failed to upload simulation data to S3: {result.s3_url}")
        logger.info("Simulation data uploaded to S3", s3_key=s3_key)
        return s3_key
