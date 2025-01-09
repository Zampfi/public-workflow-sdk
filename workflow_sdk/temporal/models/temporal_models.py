from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Mapping, Optional, Sequence, Type, Union

from temporalio.api.common.v1 import Payload
from temporalio.client import (ListWorkflowsInput, StartWorkflowInput,
                               WorkflowExecution, WorkflowExecutionStatus)
from temporalio.common import (RetryPolicy, SearchAttributes,
                               TypedSearchAttributes, WorkflowIDConflictPolicy,
                               WorkflowIDReusePolicy)


@dataclass
class ErrorResponse:
    message: str | None = None
    code: str | None = None
    internal_error: Mapping[str, Any] = field(default_factory=dict)
    external_error: Mapping[str, Any] = field(default_factory=dict)

class WorkflowExecutionStatus(Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    TERMINATED = "TERMINATED"
    CONTINUED_AS_NEW = "CONTINUED_AS_NEW"
    TIMED_OUT = "TIMED_OUT"


@dataclass
class RunWorkflowParams:
    # Required fields
    workflow: type
    id: str
    task_queue: str
    arg: Any = None  # Default to None if not provided

    # Optional fields with defaults
    execution_timeout: timedelta | None = None
    run_timeout: timedelta | None = None
    task_timeout: timedelta | None = None
    id_reuse_policy: WorkflowIDReusePolicy = WorkflowIDReusePolicy.REJECT_DUPLICATE
    id_conflict_policy: WorkflowIDConflictPolicy = WorkflowIDConflictPolicy.FAIL
    retry_policy: RetryPolicy | None = None
    cron_schedule: str = ""
    memo: Mapping[str, Any] | None = field(default_factory=dict)
    search_attributes: SearchAttributes | TypedSearchAttributes | None = None
    start_delay: timedelta | None = None
    headers: Mapping[str, Payload] = field(default_factory=dict)
    start_signal: str | None = None
    start_signal_args: Sequence[Any] | None = field(default_factory=tuple)
    ret_type: type | None = None
    rpc_metadata: Mapping[str, str] = field(default_factory=dict)
    rpc_timeout: timedelta | None = None
    request_eager_start: bool = False

    def to_start_input(self) -> StartWorkflowInput:
        """Convert to StartWorkflowInput"""
        return StartWorkflowInput(
            workflow=self.workflow,
            args=(self.arg,) if self.arg is not None else (),  # Handle None case
            id=self.id,
            task_queue=self.task_queue,
            execution_timeout=self.execution_timeout,
            run_timeout=self.run_timeout,
            task_timeout=self.task_timeout,
            id_reuse_policy=self.id_reuse_policy,
            id_conflict_policy=self.id_conflict_policy,
            retry_policy=self.retry_policy,
            cron_schedule=self.cron_schedule,
            memo=self.memo,
            search_attributes=self.search_attributes,
            start_delay=self.start_delay,
            headers=self.headers,
            start_signal=self.start_signal,
            start_signal_args=self.start_signal_args or (),
            ret_type=self.ret_type,
            rpc_metadata=self.rpc_metadata,
            rpc_timeout=self.rpc_timeout,
            request_eager_start=self.request_eager_start,
        )

@dataclass
class RunWorkflowResponse:
    error: ErrorResponse | None = None
    result: Any | None = None
    run_id: str | None = None

@dataclass
class ListWorkflowParams(ListWorkflowsInput):
    next_page_token: bytes | None = None
    rpc_metadata: Mapping[str, str] = field(default_factory=dict)
    rpc_timeout: timedelta | None = None
    limit: int | None = None

@dataclass
class WorkflowResponse:
    workflow_id: str
    run_id: str
    workflow_type: str
    task_queue: str
    error: ErrorResponse | None = None
    status: WorkflowExecutionStatus | None = None
    start_time: datetime | None = None
    close_time: datetime | None = None
    execution_time: datetime | None = None
    history_length: int | None = None
    search_attributes: dict | None = None

    @classmethod
    def from_workflow_execution(cls, workflow: WorkflowExecution):
        return cls(
            workflow_id=workflow.id,
            run_id=workflow.run_id,
            workflow_type=workflow.workflow_type,
            task_queue=workflow.task_queue,
            status=WorkflowExecutionStatus(workflow.status.name) if workflow.status else None,
            start_time=workflow.start_time,
            close_time=workflow.close_time,
            execution_time=workflow.execution_time,
            history_length=workflow.history_length,
            search_attributes=workflow.search_attributes,
        )


@dataclass
class GetWorkflowDetailsParams:
    workflow_id: str
    run_id: str | None = None

@dataclass
class WorkflowDetailsResponse:
    details: WorkflowResponse
    history: list[dict]
    error: ErrorResponse | None = None


@dataclass
class QueryWorkflowParams:
    workflow_id: str
    query: str
    args: Any | None = None
    run_id: str | None = None

@dataclass
class QueryWorkflowResponse:
    response: Any = None
    context: str | None = None
    error: ErrorResponse | None = None


@dataclass
class SignalWorkflowParams:
    workflow_id: str
    signal_name: str
    run_id: str | None = None
    args: Any | None = None

@dataclass
class SignalWorkflowResponse:
    error: ErrorResponse | None = None

@dataclass
class CancelWorkflowParams:
    workflow_id: str
    run_id: str | None = None

@dataclass
class CancelWorkflowResponse:
    error: ErrorResponse | None = None

@dataclass
class TerminateWorkflowParams:
    workflow_id: str
    run_id: str | None = None
    reason: str | None = None

@dataclass
class TerminateWorkflowResponse:
    error: ErrorResponse | None = None
