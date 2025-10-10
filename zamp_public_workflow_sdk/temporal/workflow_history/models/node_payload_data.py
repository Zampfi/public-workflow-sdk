"""
NodePayloadData model for temporal workflow operations.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class NodePayloadData(BaseModel):
    """Node data with all events, input and output payloads."""

    node_id: str = Field(..., description="Unique identifier for the node")
    input_payload: Optional[Dict[str, Any]] = Field(
        default=None, description="Input payload data for the node"
    )
    output_payload: Optional[Dict[str, Any]] = Field(
        default=None, description="Output payload data for the node"
    )
    node_events: List[Dict] = Field(..., description="List of workflow events")
