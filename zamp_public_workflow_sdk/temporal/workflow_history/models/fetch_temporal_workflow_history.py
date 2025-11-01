from __future__ import annotations
from pydantic import BaseModel, Field
from temporalio.client import WorkflowHistory as TemporalWorkflowHistory
from zamp_public_workflow_sdk.temporal.workflow_history.models.workflow_history import WorkflowHistory


class FetchTemporalWorkflowHistoryInput(BaseModel):
    """Input model for fetching temporal workflow history"""

    workflow_id: str = Field(..., min_length=1, description="Workflow ID to fetch")
    run_id: str = Field(..., min_length=1, description="Run ID to fetch")
    node_ids: list[str] | None = Field(default=None, description="Filter by specific node IDs")
    prefix_node_ids: list[str] | None = Field(default=None, description="Filter by node ID prefixes")
    decode_payloads: bool = Field(
        default=True, description="Whether to decode payloads. Set to False to preserve encoded payloads with metadata."
    )


class FetchTemporalWorkflowHistoryOutput(WorkflowHistory):
    """Output model for fetched temporal workflow history - inherits directly from WorkflowHistory to avoid nesting"""

    pass


class FetchWorkflowHistoryFromApiInput(BaseModel):
    """Input model for fetching workflow history from Temporal API."""

    workflow_id: str = Field(..., description="The workflow ID")
    run_id: str = Field(..., description="The workflow run ID")


class FetchWorkflowHistoryFromApiOutput(BaseModel):
    """
    Pydantic wrapper for TemporalWorkflowHistory from Temporal API.

    This wraps the TemporalWorkflowHistory object and provides methods
    to convert it to the standard WorkflowHistory Pydantic model.
    """

    workflow_id: str = Field(..., description="The workflow ID")
    run_id: str = Field(..., description="The workflow run ID")
    events: list[dict] = Field(..., description="List of workflow events from Temporal API")

    @classmethod
    def from_temporal_history(
        cls, temporal_history: TemporalWorkflowHistory, workflow_id: str, run_id: str
    ) -> FetchWorkflowHistoryFromApiOutput:
        """
        Create FetchWorkflowHistoryFromApiOutput from TemporalWorkflowHistory.

        Args:
            temporal_history: The TemporalWorkflowHistory object from Temporal API
            workflow_id: The workflow ID
            run_id: The workflow run ID

        Returns:
            FetchWorkflowHistoryFromApiOutput instance
        """
        history_dict = temporal_history.to_json_dict()
        return cls(
            workflow_id=history_dict.get("workflow_id", workflow_id),
            run_id=history_dict.get("run_id", run_id),
            events=history_dict.get("events", []),
        )
