from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.simulation.models.config import SimulationConfig


class SimulationConfigBuilderInput(BaseModel):
    """Input for generating simulation config from workflow history."""

    workflow_id: str = Field(..., description="Workflow ID to extract node IDs from")
    run_id: str = Field(..., description="Run ID to extract node IDs from")
    execute_actions: list[str] | None = Field(
        default=None, description="List of node IDs to execute (not mock). These will be added to the skip list."
    )


class SimulationConfigBuilderOutput(BaseModel):
    """Output for generating simulation config from workflow history."""

    simulation_config: SimulationConfig = Field(..., description="Generated simulation configuration")
