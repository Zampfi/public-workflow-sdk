from typing import Any

from pydantic import BaseModel, Field


class NodePayload(BaseModel):
    """
    Represents input and output payloads for a node in simulation.

    This model is used to store the payloads that will be used to mock
    activity/workflow executions during simulation.
    """

    node_id: str = Field(
        description="The Node ID of the payload",
    )
    input_payload: Any | None = Field(
        default=None,
        description="Input payload data for the node (may be encoded or raw)",
    )
    output_payload: Any | None = Field(
        default=None,
        description="Output payload data for the node (may be encoded or raw)",
    )
