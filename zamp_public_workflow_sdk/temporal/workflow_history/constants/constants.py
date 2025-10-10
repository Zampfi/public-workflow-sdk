"""
Constants and enums for temporal workflow operations.
"""

from enum import Enum


class EventType(Enum):
    """Temporal workflow event types."""

    WORKFLOW_EXECUTION_STARTED = "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED"
    WORKFLOW_EXECUTION_COMPLETED = "EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED"
    ACTIVITY_TASK_SCHEDULED = "EVENT_TYPE_ACTIVITY_TASK_SCHEDULED"
    ACTIVITY_TASK_COMPLETED = "EVENT_TYPE_ACTIVITY_TASK_COMPLETED"
    WORKFLOW_TASK_SCHEDULED = "EVENT_TYPE_WORKFLOW_TASK_SCHEDULED"
    WORKFLOW_TASK_STARTED = "EVENT_TYPE_WORKFLOW_TASK_STARTED"
    WORKFLOW_TASK_COMPLETED = "EVENT_TYPE_WORKFLOW_TASK_COMPLETED"
    ACTIVITY_TASK_STARTED = "EVENT_TYPE_ACTIVITY_TASK_STARTED"
    START_CHILD_WORKFLOW_EXECUTION_INITIATED = (
        "EVENT_TYPE_START_CHILD_WORKFLOW_EXECUTION_INITIATED"
    )
    CHILD_WORKFLOW_EXECUTION_STARTED = "EVENT_TYPE_CHILD_WORKFLOW_EXECUTION_STARTED"
    CHILD_WORKFLOW_EXECUTION_COMPLETED = "EVENT_TYPE_CHILD_WORKFLOW_EXECUTION_COMPLETED"


class PayloadField(Enum):
    """Payload field names."""

    INPUT = "input"
    RESULT = "result"
    PAYLOADS = "payloads"
    DATA = "data"
    METADATA = "metadata"
    ENCODING = "encoding"
    HEADER = "header"
    FIELDS = "fields"


class EventField(Enum):
    """Event field names."""

    NODE_ID = "node_id"
    EVENT_ID = "eventId"
    SCHEDULED_EVENT_ID = "scheduledEventId"
    INITIATED_EVENT_ID = "initiatedEventId"
    EVENT_TYPE = "eventType"


class EventTypeToAttributesKey(Enum):
    WORKFLOW_EXECUTION_STARTED = "workflowExecutionStartedEventAttributes"
    WORKFLOW_EXECUTION_COMPLETED = "workflowExecutionCompletedEventAttributes"
    ACTIVITY_TASK_SCHEDULED = "activityTaskScheduledEventAttributes"
    ACTIVITY_TASK_COMPLETED = "activityTaskCompletedEventAttributes"
    WORKFLOW_TASK_SCHEDULED = "workflowTaskScheduledEventAttributes"
    WORKFLOW_TASK_STARTED = "workflowTaskStartedEventAttributes"
    WORKFLOW_TASK_COMPLETED = "workflowTaskCompletedEventAttributes"
    ACTIVITY_TASK_STARTED = "activityTaskStartedEventAttributes"
    START_CHILD_WORKFLOW_EXECUTION_INITIATED = (
        "startChildWorkflowExecutionInitiatedEventAttributes"
    )
    CHILD_WORKFLOW_EXECUTION_STARTED = "childWorkflowExecutionStartedEventAttributes"
    CHILD_WORKFLOW_EXECUTION_COMPLETED = (
        "childWorkflowExecutionCompletedEventAttributes"
    )

def get_workflow_history_file_name(workflow_id: str, run_id: str) -> str:
    """
    Generate the file name for workflow history stored in S3.

    Args:
        workflow_id: The workflow ID
        run_id: The run ID

    Returns:
        The file name in format: {workflow_id}_{run_id}.json
    """
    return f"{workflow_id}_{run_id}.json"
