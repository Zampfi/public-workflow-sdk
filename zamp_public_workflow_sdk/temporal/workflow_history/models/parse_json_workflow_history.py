"""
Models for parsing JSON workflow history from blob storage.
"""

from pydantic import BaseModel, Field


class ParseJsonWorkflowHistoryInput(BaseModel):
    """Input for parsing JSON workflow history from blob storage."""

    content_base64: str = Field(
        ..., description="Base64 encoded JSON content from blob storage"
    )
    workflow_id: str = Field(..., description="Expected workflow ID")
    run_id: str = Field(..., description="Expected run ID")
