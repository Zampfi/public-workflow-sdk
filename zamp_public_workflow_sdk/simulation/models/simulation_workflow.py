from typing import Any

from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.simulation.models.config import SimulationConfig


class SimulationWorkflowInput(BaseModel):
    simulation_config: SimulationConfig = Field(..., description="Simulation config")


class SimulationWorkflowOutput(BaseModel):
    node_id_to_response_map: dict[str, Any] = Field(..., description="Response map")
