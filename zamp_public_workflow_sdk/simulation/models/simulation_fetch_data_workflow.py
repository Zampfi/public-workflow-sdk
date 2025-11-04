from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.simulation.models.config import SimulationConfig
from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload


class SimulationFetchDataWorkflowInput(BaseModel):
    simulation_config: SimulationConfig = Field(..., description="Simulation config")


class SimulationFetchDataWorkflowOutput(BaseModel):
    node_id_to_payload_map: dict[str, NodePayload] = Field(
        ..., description="Map of node IDs to their input and output payloads"
    )
