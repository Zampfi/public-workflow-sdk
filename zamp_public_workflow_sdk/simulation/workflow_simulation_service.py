"""
Workflow Simulation Service for managing simulation state and responses.
"""

from datetime import timedelta
from typing import Any

import structlog
from temporalio import workflow
from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse
from zamp_public_workflow_sdk.simulation.models.config import SimulationConfig
from zamp_public_workflow_sdk.simulation.models.simulation_strategy import (
    NodeStrategy,
    StrategyType,
)
from zamp_public_workflow_sdk.simulation.models.simulation_workflow import (
    SimulationWorkflowInput,
)
from zamp_public_workflow_sdk.simulation.strategies.base_strategy import BaseStrategy
from zamp_public_workflow_sdk.simulation.strategies.custom_output_strategy import (
    CustomOutputStrategyHandler,
)
from zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy import (
    TemporalHistoryStrategyHandler,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import (
    DecodeNodePayloadInput,
)

logger = structlog.get_logger(__name__)


class WorkflowSimulationService:
    """
    Service for managing workflow simulation state and responses.

    This service pre-computes simulation responses during initialization
    """

    def __init__(self, simulation_config: SimulationConfig):
        """
        Initialize simulation service with configuration.

        Args:
            simulation_config: Simulation configuration
        """
        self.simulation_config = simulation_config
        # this response is raw response to be set using FetchWorkflowHistoryWorkflow
        self.node_id_to_response_map: dict[str, Any] = {}

    async def _initialize_simulation_data(self) -> None:
        """
        Initialize simulation data by pre-computing all responses.

        This method builds the node_id_to_response_map by processing
        all strategies in the simulation configuration.
        This method should be called from within a workflow context.
        """
        logger.info(
            "Initializing simulation data",
            config_version=self.simulation_config.version,
        )

        from zamp_public_workflow_sdk.actions_hub import ActionsHub
        from zamp_public_workflow_sdk.simulation.workflows.simulation_workflow import (
            SimulationWorkflow,
        )

        try:
            workflow_result = await ActionsHub.execute_child_workflow(
                SimulationWorkflow,
                SimulationWorkflowInput(simulation_config=self.simulation_config),
            )

            logger.info(
                "SimulationWorkflow completed",
                workflow_result=workflow_result,
                has_node_id_to_response_map=workflow_result is not None
                and hasattr(workflow_result, "node_id_to_response_map"),
            )

            self.node_id_to_response_map = workflow_result.node_id_to_response_map

            logger.info(
                "Simulation data initialized successfully",
                total_nodes=len(self.node_id_to_response_map),
            )

        except Exception as e:
            logger.error(
                "Failed to execute SimulationWorkflow",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_simulation_response(self, node_id: str, action_name: str | None = None) -> SimulationResponse:
        """
        Get simulation response for a specific node and decode if needed.

        This method automatically handles decoding of encoded payloads from TemporalHistoryStrategy.
        CustomOutputStrategy returns raw values without encoding, so no decoding is needed.

        Args:
            node_id: The node execution ID
            action_name: Optional action name for activity summary during decoding

        Returns:
            SimulationResponse with MOCK if node should be mocked (decoded if needed), EXECUTE otherwise
        """

        # check if node is in the response map
        is_response_mocked = node_id in self.node_id_to_response_map
        if not is_response_mocked:
            return SimulationResponse(execution_type=ExecutionType.EXECUTE, execution_response=None)

        # If node is in the response map, it should be mocked
        payload = self.node_id_to_response_map[node_id]
        simulation_response = SimulationResponse(
            execution_type=ExecutionType.MOCK,
        )
        # Only decode if payload has "metadata" with "encoding" (from TemporalHistoryStrategy)
        # CustomOutputStrategy returns raw values without encoding
        needs_decoding = (
            payload and isinstance(payload, dict) and payload.get("metadata", {}).get("encoding") is not None
        )
        if needs_decoding:
            try:
                decoded_payload = await workflow.execute_activity(
                    "decode_node_payload",
                    DecodeNodePayloadInput(node_id=node_id, encoded_payload=payload),
                    summary=action_name,
                    start_to_close_timeout=timedelta(seconds=30),
                )
                simulation_response.execution_response = decoded_payload
            except Exception as e:
                logger.error(
                    "Failed to decode simulation payload",
                    node_id=node_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise e
        return simulation_response

    @staticmethod
    def get_strategy(node_strategy: NodeStrategy) -> BaseStrategy | None:
        """
        Create strategy handler based on strategy type.

        Args:
            node_strategy: NodeStrategy object containing strategy configuration

        Returns:
            Instance of the appropriate strategy handler or None if unknown type
        """
        match node_strategy.strategy.type:
            case StrategyType.TEMPORAL_HISTORY:
                temporal_config = node_strategy.strategy.config
                return TemporalHistoryStrategyHandler(
                    reference_workflow_id=temporal_config.reference_workflow_id,
                    reference_workflow_run_id=temporal_config.reference_workflow_run_id,
                )
            case StrategyType.CUSTOM_OUTPUT:
                custom_config = node_strategy.strategy.config
                return CustomOutputStrategyHandler(output_value=custom_config.output_value)
            case _:
                logger.error("Unknown strategy type", strategy_type=node_strategy.strategy.type)
                raise ValueError(f"Unknown strategy type: {node_strategy.strategy.type}")
