"""
Common models for ActionsHub - independent of Pantheon platform.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from .decorators import external


@external
class ZampMetadataContext(BaseModel):
    """
    Model containing metadata context for Zamp platform operations.

    Provides essential context information including user, organization,
    and dataset details for workflow execution to pass contextual information
    through processing workflows.
    """

    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="User ID")
    process_id: str = Field(..., description="Process ID")
    dataset_metadata_context: Optional[Dict[str, str]] = Field(
        None, description="Dataset Metadata Context"
    )
