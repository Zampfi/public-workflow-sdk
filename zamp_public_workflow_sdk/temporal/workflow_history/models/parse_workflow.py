from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.temporal.workflow_history.models.file import File
from zamp_public_workflow_sdk.temporal.workflow_history.models.workflow_history import (
    WorkflowHistory,
)


class ParseWorkflowHistoryProtoInput(BaseModel):
    proto_file: File = Field(..., description="File object containing the proto bytes file")


class ParseWorkflowHistoryProtoOutput(BaseModel):
    workflow_histories: list[WorkflowHistory] = Field(
        ..., description="List of parsed workflow histories from the protobuf data"
    )
