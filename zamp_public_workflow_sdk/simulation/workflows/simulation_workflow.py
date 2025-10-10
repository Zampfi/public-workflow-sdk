from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from zamp_public_workflow_sdk.actions_hub import ActionsHub
    from zamp_public_workflow_sdk.simulation.models.simulation_workflow import (
        SimulationWorkflowInput,
        SimulationWorkflowOutput,
    )
    import structlog


logger = structlog.get_logger(__name__)


@ActionsHub.register_workflow_defn(
    "Workflow that fetches simulation data using strategy pattern",
    labels=["simulation", "strategy"],
)
class SimulationWorkflow:
    def __init__(self):
        pass

    @ActionsHub.register_workflow_run
    async def execute(self, input: SimulationWorkflowInput) -> SimulationWorkflowOutput:
        """
        Execute the simulation data workflow to fetch and process workflow history.

        Args:
            input: Contains simulation configuration with node strategies

        Returns:
            Mapping of node IDs to their response data
        """
        from zamp_public_workflow_sdk.simulation.workflow_simulation_service import (
            WorkflowSimulationService,
        )

        node_id_to_response_map = {}

        for node_strategy in input.simulation_config.mock_config.node_strategies:
            strategy = WorkflowSimulationService.get_strategy(node_strategy)
            if strategy is None:
                continue
            try:
                result = await strategy.execute(
                    node_ids=node_strategy.nodes,
                )
                node_id_to_response_map.update(result.node_outputs)
            except Exception as e:
                logger.error(
                    "Error processing node with strategy",
                    node_ids=node_strategy.nodes,
                    strategy_type=node_strategy.strategy.type,
                    error=str(e),
                    error_type=type(e).__name__,
                )

        return SimulationWorkflowOutput(node_id_to_response_map=node_id_to_response_map)
