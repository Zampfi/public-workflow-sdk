from typing import List, Optional
from pydantic import BaseModel, Field
from zamp_public_workflow_sdk.temporal.workflow_history.models.workflow_history import (
    WorkflowHistory,
)


class FetchTemporalWorkflowHistoryInput(BaseModel):
    """Input model for fetching temporal workflow history"""

    workflow_id: str = Field(..., min_length=1, description="Workflow ID to fetch")
    run_id: str = Field(..., min_length=1, description="Run ID to fetch")
    node_ids: Optional[List[str]] = Field(
        default=None, description="Filter by specific node IDs"
    )
    prefix_node_ids: Optional[List[str]] = Field(
        default=None, description="Filter by node ID prefixes"
    )


class FetchTemporalWorkflowHistoryOutput(WorkflowHistory):
    """Output model for fetched temporal workflow history - inherits directly from WorkflowHistory to avoid nesting"""

    pass
