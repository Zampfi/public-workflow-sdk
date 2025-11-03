from typing import Any

from pydantic import BaseModel, Field


class NodePayload(BaseModel):
    """
    Represents input and output payloads for a node in simulation.

    This model is used to store the payloads that will be used to mock
    activity/workflow executions during simulation.
    """

    input_payload: Any | None = Field(
        default=None,
        description="Input payload data for the node (may be encoded or raw)",
    )
    output_payload: Any | None = Field(
        default=None,
        description="Output payload data for the node (may be encoded or raw)",
    )
    # Metadata for child workflow traversal
    needs_child_traversal: bool = Field(
        default=False,
        description="Flag indicating if child workflow needs to be traversed",
    )
    child_workflow_id: str | None = Field(
        default=None,
        description="Child workflow ID if traversal is needed",
    )
    child_run_id: str | None = Field(
        default=None,
        description="Child workflow run ID if traversal is needed",
    )
