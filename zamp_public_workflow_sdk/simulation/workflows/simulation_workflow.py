from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import structlog
    from typing import Any
    from zamp_public_workflow_sdk.actions_hub import ActionsHub
    from zamp_public_workflow_sdk.simulation.models.simulation_workflow import (
        SimulationWorkflowOutput,
        SimulationWorkflowInput,
    )
    from zamp_public_workflow_sdk.simulation.helper import build_node_payload


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

        node_payloads = await build_node_payload(
            workflow_id=workflow_id,
            run_id=run_id,
            output_config=input_params.output_schema.node_payloads,
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
