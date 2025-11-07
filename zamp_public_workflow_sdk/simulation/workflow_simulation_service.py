"""
Workflow Simulation Service for managing simulation state and responses.
"""

import structlog
from zamp_public_workflow_sdk.simulation.models import (
    ExecutionType,
    SimulationResponse,
    NodePayload,
    SimulationFetchDataWorkflowInput,
)
from zamp_public_workflow_sdk.simulation.models.config import SimulationConfig
from zamp_public_workflow_sdk.simulation.models.simulation_strategy import (
    NodeStrategy,
    StrategyType,
)
from zamp_public_workflow_sdk.simulation.strategies.base_strategy import BaseStrategy
from zamp_public_workflow_sdk.simulation.strategies.custom_output_strategy import (
    CustomOutputStrategyHandler,
)
from zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy import (
    TemporalHistoryStrategyHandler,
)
from zamp_public_workflow_sdk.simulation.models.mocked_result import MockedResultInput, MockedResultOutput

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
        self.node_id_to_payload_map: dict[str, NodePayload] = {}

    async def _initialize_simulation_data(self) -> None:
        """
        Initialize simulation data by pre-computing all responses.

        This method builds the node_id_to_payload_map by processing
        all strategies in the simulation configuration.
        This method should be called from within a workflow context.
        """
        logger.info(
            "Initializing simulation data",
            config_version=self.simulation_config.version,
        )

        from zamp_public_workflow_sdk.actions_hub import ActionsHub
        from zamp_public_workflow_sdk.simulation.workflows.simulation_fetch_data_workflow import (
            SimulationFetchDataWorkflow,
        )

        try:
            workflow_result = await ActionsHub.execute_child_workflow(
                SimulationFetchDataWorkflow,
                SimulationFetchDataWorkflowInput(simulation_config=self.simulation_config),
            )

            logger.info(
                "SimulationFetchDataWorkflow completed",
                has_node_id_to_payload_map=workflow_result is not None
                and hasattr(workflow_result, "node_id_to_payload_map"),
            )

            self.node_id_to_payload_map = workflow_result.node_id_to_payload_map

            logger.info(
                "Simulation data initialized successfully",
                total_nodes=len(self.node_id_to_payload_map),
            )

        except Exception as e:
            logger.error(
                "Failed to execute SimulationFetchDataWorkflow",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_simulation_response(self, node_id: str, action_name: str | None = None) -> SimulationResponse:
        """
        Get simulation response for a specific node by calling return_mocked_result activity.

        This method delegates the decoding of encoded payloads to the return_mocked_result activity,
        which runs in API mode and handles both TemporalHistoryStrategy (encoded) and
        CustomOutputStrategy (raw) outputs.

        Args:
            node_id: The node execution ID
            action_name: Optional action name for activity summary

        Returns:
            SimulationResponse with MOCK if node should be mocked (decoded if needed), EXECUTE otherwise
        """
        from zamp_public_workflow_sdk.actions_hub import ActionsHub

        # check if node is in the response map
        is_response_mocked = node_id in self.node_id_to_payload_map
        if not is_response_mocked:
            return SimulationResponse(execution_type=ExecutionType.EXECUTE, execution_response=None)

        # If node is in the response map, it should be mocked
        # node_payload is a NodePayload instance with input_payload and output_payload attributes
        node_payload = self.node_id_to_payload_map[node_id]

        try:
            decoded_result: MockedResultOutput = await ActionsHub.execute_activity(
                "return_mocked_result",
                MockedResultInput(
                    node_id=node_id,
                    input_payload=node_payload.input_payload,
                    output_payload=node_payload.output_payload,
                    action_name=action_name,
                ),
                return_type=MockedResultOutput,
                custom_node_id=node_id,
                summary=action_name,
            )

            return SimulationResponse(
                execution_type=ExecutionType.MOCK,
                execution_response=decoded_result.root,
            )
        except Exception as e:
            logger.error(
                "Failed to get mocked result",
                node_id=node_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

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
