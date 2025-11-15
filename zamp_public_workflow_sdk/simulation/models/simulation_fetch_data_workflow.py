from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.simulation.models.config import SimulationConfig
from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload


class SimulationFetchDataWorkflowInput(BaseModel):
    simulation_config: SimulationConfig = Field(..., description="Simulation config")
    workflow_id: str = Field(..., description="Workflow ID for S3 key generation")


class SimulationFetchDataWorkflowOutput(BaseModel):
    node_id_to_payload_map: dict[str, NodePayload] = Field(
        ..., description="Map of node IDs to their input and output payloads"
    )
    s3_key: str | None = Field(default=None, description="S3 key where the simulation data is stored")
