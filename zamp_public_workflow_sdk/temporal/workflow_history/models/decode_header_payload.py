from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class DecodeHeadersInput(BaseModel):
    """Helper class for decode headers activity input"""

    events: List[Dict[str, Any]] = Field(
        ..., description="List of temporal workflow events to decode headers from"
    )


class DecodeHeadersOutput(BaseModel):
    """Helper class for decode headers activity output"""

    decoded_events: List[Dict[str, Any]] = Field(
        ..., description="List of temporal workflow events with decoded headers"
    )


class DecodePayloadsInput(BaseModel):
    """Helper class for decode payloads activity input"""

    events: List[Dict[str, Any]] = Field(
        ..., description="List of temporal workflow events to decode payloads from"
    )
    node_ids: Optional[List[str]] = Field(
        default=None, description="List of node identifiers for payload decoding"
    )
    prefix_node_ids: Optional[List[str]] = Field(
        default=None, description="List of node ID prefixes for partial matching"
    )


class DecodePayloadsOutput(BaseModel):
    """Helper class for decode payloads activity output"""

    decoded_events: List[Dict[str, Any]] = Field(
        ..., description="List of temporal workflow events with decoded payloads"
    )
