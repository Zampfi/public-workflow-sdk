"""
NodePayloadData model for temporal workflow operations.
"""

from typing import Any

from pydantic import BaseModel, Field


class NodePayloadData(BaseModel):
    """Node data with all events, input and output payloads."""

    node_id: str = Field(..., description="Unique identifier for the node")
    input_payload: dict[str, Any] | None = Field(default=None, description="Input payload data for the node")
    output_payload: dict[str, Any] | None = Field(default=None, description="Output payload data for the node")
    node_events: list[dict] = Field(..., description="List of workflow events")


class DecodeNodePayloadInput(BaseModel):
    """Input model for decode_node_payload activity.

    The encoded_payload should be a dict with PayloadKey.INPUT_PAYLOAD and PayloadKey.OUTPUT_PAYLOAD keys:
    {
        PayloadKey.INPUT_PAYLOAD: {...},   # encoded input payload
        PayloadKey.OUTPUT_PAYLOAD: {...}   # encoded output payload
    }

    Note: PayloadKey is from zamp_public_workflow_sdk.simulation.constants
    """

    node_id: str = Field(..., description="The node ID")
    encoded_payload: dict[str, Any] = Field(
        ...,
        description="Dict with PayloadKey.INPUT_PAYLOAD and PayloadKey.OUTPUT_PAYLOAD keys containing encoded payloads",
    )


class DecodeNodePayloadOutput(BaseModel):
    """Output model for decode_node_payload activity."""

    result: Any = Field(..., description="The decoded payload result")
