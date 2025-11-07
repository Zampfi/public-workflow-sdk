from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_serializer


class NodePayloadType(str, Enum):
    """Type of payload data to extract from workflow history."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    INPUT_OUTPUT = "INPUT_OUTPUT"


class NodePayloadResult(BaseModel):
    """Result for a single activity payload extraction from workflow history.

    Contains the extracted input and/or output data for an activity execution.
    Only includes fields that are not None.
    """

    node_id: str = Field(description="Node ID of the activity (e.g., 'activity_name#1')")
    input: Any | None = Field(
        default=None,
        description="Activity input parameters if extracted (based on payload type)",
    )
    output: Any | None = Field(
        default=None,
        description="Activity output result if extracted (based on payload type)",
    )

    @model_serializer
    def serialize_model(self) -> dict[str, Any]:
        """Custom serializer that returns {node_id: {input/output}} format."""
        payload = {}
        if self.input is not None:
            payload["input"] = self.input
        if self.output is not None:
            payload["output"] = self.output
        return {self.node_id: payload}
