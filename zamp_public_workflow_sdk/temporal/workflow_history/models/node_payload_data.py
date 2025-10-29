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
    """Input model for decode_node_payload activity."""

    node_id: str = Field(..., description="The node ID")
    encoded_payload: dict[str, Any] = Field(..., description="The encoded payload to decode")
