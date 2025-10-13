"""
Configurable log mode interceptor for Temporal workflows and activities.

This interceptor extracts log_mode from workflow and activity arguments
and binds it to the Python context for structured logging.

Usage:
------
1. Add the interceptor to your worker configuration:

   from zamp_public_workflow_sdk.temporal.interceptors.log_mode_interceptor import LogModeInterceptor
   import structlog

   interceptors = [
       LogModeInterceptor(
           logger_module=structlog,
           context_bind_fn=structlog.contextvars.bind_contextvars,
       ),
       # ... other interceptors
   ]

2. Pass log_mode as an attribute in your workflow/activity arguments:

   from pydantic import BaseModel
   from zamp_public_workflow_sdk.actions_hub.constants import LogMode

   class MyWorkflowInput(BaseModel):
       data: str
       log_mode: LogMode  # or log_mode: str

   @workflow.defn
   class MyWorkflow:
       @workflow.run
       async def run(self, input: MyWorkflowInput) -> str:
           # The LogModeInterceptor will automatically extract log_mode
           # and bind it to structlog context
           workflow.logger.info("This will use the log_mode from input")
           return "done"

3. The log_mode will be automatically propagated to:
   - Child workflows
   - Activities
   - Local activities
   - Signals

   You don't need to pass log_mode explicitly to child workflows/activities;
   it will be propagated through headers automatically.

Example:
--------
# Start a workflow with DEBUG log mode
client.execute_workflow(
    MyWorkflow.run,
    MyWorkflowInput(data="test", log_mode=LogMode.DEBUG),
    id="my-workflow-id",
    task_queue="my-task-queue",
)

# All child workflows and activities will inherit the DEBUG log mode
"""

from typing import Any, Callable

from temporalio import activity, workflow
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    ExecuteWorkflowInput,
    Interceptor,
    SignalChildWorkflowInput,
    SignalExternalWorkflowInput,
    StartActivityInput,
    StartChildWorkflowInput,
    StartLocalActivityInput,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
    WorkflowOutboundInterceptor,
)

# Constant for the log mode field name
LOG_MODE_FIELD = "log_mode"


# Activity interceptor
class LogModeActivityInterceptor(ActivityInboundInterceptor):
    def __init__(
        self,
        next_interceptor: ActivityInboundInterceptor,
        context_bind_fn: Callable,
        logger: Any,
    ):
        super().__init__(next_interceptor)
        self.context_bind_fn = context_bind_fn
        self.logger = logger

    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        # Extract log_mode from args if present
        log_mode = self._extract_log_mode_from_args(input.args)

        # If not in args, check headers (from parent workflow)
        if log_mode is None:
            log_mode = self._extract_log_mode_from_headers(input.headers)

        # Bind log_mode to context if found
        if log_mode is not None:
            try:
                self.context_bind_fn(log_mode=log_mode)
            except Exception as e:
                self.logger.error(f"Error binding log_mode to context: {str(e)}")

        return await self.next.execute_activity(input)

    def _extract_log_mode_from_args(self, args: tuple) -> str | None:
        """Extract log_mode from args"""
        for arg in args:
            # Check if arg has log_mode attribute
            if hasattr(arg, LOG_MODE_FIELD):
                log_mode = getattr(arg, LOG_MODE_FIELD)
                # Handle both enum and string
                if hasattr(log_mode, "value"):
                    return log_mode.value
                return str(log_mode)
        return None

    def _extract_log_mode_from_headers(self, headers: dict) -> str | None:
        """Extract log_mode from headers"""
        if LOG_MODE_FIELD in headers:
            try:
                payload = headers.get(LOG_MODE_FIELD)
                log_mode = activity.payload_converter().from_payload(payload, str)
                return log_mode
            except Exception as e:
                self.logger.error(f"Error extracting log_mode from headers: {str(e)}")
        return None


# Workflow inbound interceptor
class LogModeWorkflowInboundInterceptor(WorkflowInboundInterceptor):
    def __init__(
        self,
        next_interceptor: WorkflowInboundInterceptor,
        context_bind_fn: Callable,
        logger: Any,
    ):
        super().__init__(next_interceptor)
        self.context_bind_fn = context_bind_fn
        self.logger = logger
        self._current_log_mode: str | None = None

    def init(self, outbound: WorkflowOutboundInterceptor) -> None:
        self.next.init(LogModeWorkflowOutboundInterceptor(outbound, self.get_log_mode))

    def get_log_mode(self) -> str | None:
        """Get the current log mode."""
        return self._current_log_mode

    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        # Extract log_mode from args if present
        log_mode = self._extract_log_mode_from_args(input.args)

        # If not in args, check headers (from parent workflow)
        if log_mode is None:
            log_mode = self._extract_log_mode_from_headers(input.headers)

        # Store log_mode for propagation to child workflows/activities
        if log_mode is not None:
            self._current_log_mode = log_mode

            # Bind log_mode to context
            with workflow.unsafe.sandbox_unrestricted():
                try:
                    self.context_bind_fn(log_mode=log_mode)
                except Exception as e:
                    self.logger.error(f"Error binding log_mode to context: {str(e)}")

        return await self.next.execute_workflow(input)

    def _extract_log_mode_from_args(self, args: tuple) -> str | None:
        """Extract log_mode from args"""
        for arg in args:
            # Check if arg has log_mode attribute
            if hasattr(arg, LOG_MODE_FIELD):
                log_mode = getattr(arg, LOG_MODE_FIELD)
                # Handle both enum and string
                if hasattr(log_mode, "value"):
                    return log_mode.value
                return str(log_mode)
        return None

    def _extract_log_mode_from_headers(self, headers: dict) -> str | None:
        """Extract log_mode from headers"""
        if LOG_MODE_FIELD in headers:
            try:
                payload = headers.get(LOG_MODE_FIELD)
                log_mode = workflow.payload_converter().from_payload(payload, str)
                self.logger.debug("Found log_mode in workflow headers", log_mode=log_mode)
                return log_mode
            except Exception as e:
                self.logger.error(f"Error extracting log_mode from headers: {str(e)}")
        return None


# Workflow outbound interceptor
class LogModeWorkflowOutboundInterceptor(WorkflowOutboundInterceptor):
    def __init__(
        self,
        next_interceptor: WorkflowOutboundInterceptor,
        get_log_mode_fn: Callable,
    ):
        super().__init__(next_interceptor)
        self.get_log_mode_fn = get_log_mode_fn

    def _add_log_mode_to_headers(self, headers: dict) -> None:
        """Add log_mode to headers for propagation"""
        log_mode = self.get_log_mode_fn()
        if log_mode is not None:
            payload = workflow.payload_converter().to_payload(log_mode)
            headers[LOG_MODE_FIELD] = payload

    def start_activity(self, input: StartActivityInput) -> Any:
        # Add log_mode to activity headers
        self._add_log_mode_to_headers(input.headers)
        return self.next.start_activity(input)

    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        # Add log_mode to child workflow headers
        self._add_log_mode_to_headers(input.headers)
        return await self.next.start_child_workflow(input)

    def start_local_activity(self, input: StartLocalActivityInput) -> Any:
        # Add log_mode to local activity headers
        self._add_log_mode_to_headers(input.headers)
        return self.next.start_local_activity(input)

    async def signal_child_workflow(self, input: SignalChildWorkflowInput) -> None:
        # Add log_mode to signal headers
        self._add_log_mode_to_headers(input.headers)
        return await self.next.signal_child_workflow(input)

    async def signal_external_workflow(self, input: SignalExternalWorkflowInput) -> None:
        # Add log_mode to signal headers
        self._add_log_mode_to_headers(input.headers)
        return await self.next.signal_external_workflow(input)


# Main interceptor
class LogModeInterceptor(Interceptor):
    """
    Configurable log mode interceptor that extracts and propagates log_mode from arguments.

    This interceptor looks for a 'log_mode' attribute in workflow and activity arguments.
    If found, it binds it to the Python context using the provided context binding function
    (typically structlog.contextvars.bind_contextvars).

    The log_mode is automatically propagated to child workflows and activities through headers,
    so they can access the same logging configuration without modifying their arguments.

    Expected usage:
    - Arguments should have a 'log_mode' attribute (can be a string or enum)
    - If log_mode is an enum, its .value will be extracted

    This interceptor extracts log_mode from incoming calls and propagates it through headers
    to child workflows/activities without modifying their arguments.
    """

    def __init__(
        self,
        logger_module: Any,
        context_bind_fn: Callable,
    ):
        """
        Initialize the log mode interceptor with configurable parameters.

        Args:
            logger_module: Logger to use for logging (must support debug and error methods)
            context_bind_fn: Function to bind context variables (e.g., structlog.contextvars.bind_contextvars)
        """
        self.logger = logger_module.get_logger(__name__)
        self.context_bind_fn = context_bind_fn

    def intercept_activity(self, next: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        return LogModeActivityInterceptor(next, self.context_bind_fn, self.logger)

    def workflow_interceptor_class(self, input: WorkflowInterceptorClassInput) -> type[WorkflowInboundInterceptor]:
        def interceptor_creator(next_interceptor):
            return LogModeWorkflowInboundInterceptor(next_interceptor, self.context_bind_fn, self.logger)

        return interceptor_creator
