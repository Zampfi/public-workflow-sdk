import uuid
from typing import Any, Callable, Optional, Type

from temporalio import activity, workflow
import contextvars
from temporalio.converter import PayloadConverter
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

# Activity interceptor
class TraceActivityInterceptor(ActivityInboundInterceptor):
    def __init__(
        self, 
        next_interceptor: ActivityInboundInterceptor,
        trace_header_key: str,
        trace_context_key: str,
        context_bind_fn: Callable
    ):
        super().__init__(next_interceptor)
        self.trace_header_key = trace_header_key
        self.trace_context_key = trace_context_key
        self.context_bind_fn = context_bind_fn

    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        if hasattr(input, "headers") and self.trace_header_key in input.headers:
            payload = input.headers.get(self.trace_header_key)
            trace_id = activity.payload_converter().from_payload(payload, str)
            self.context_bind_fn(**{self.trace_context_key: trace_id})
            
        return await self.next.execute_activity(input)

# Workflow inbound interceptor
class TraceWorkflowInboundInterceptor(WorkflowInboundInterceptor):
    def __init__(
        self, 
        next_interceptor: WorkflowInboundInterceptor,
        trace_header_key: str,
        trace_context_key: str,
        context_bind_fn: Callable,
        logger: Any
    ):
        super().__init__(next_interceptor)
        self.trace_header_key = trace_header_key
        self.trace_context_key = trace_context_key
        self.context_bind_fn = context_bind_fn
        self.logger = logger
        self._current_trace_id = None

    def init(self, outbound: WorkflowOutboundInterceptor) -> None:
        self.next.init(TraceWorkflowOutboundInterceptor(
            outbound,
            self.trace_header_key,
            self.trace_context_key,
            self.get_trace_id
        ))

    def get_trace_id(self) -> Optional[str]:
        """Get the current trace ID."""
        return self._current_trace_id

    async def execute_workflow(self, input: ExecuteWorkflowInput) -> any:
        info = workflow.info()
        
        # Get trace ID from headers or use workflow ID
        trace_id = None
        if hasattr(input, "headers") and self.trace_header_key in input.headers:
            payload = input.headers.get(self.trace_header_key)
            trace_id = workflow.payload_converter().from_payload(payload, str)
            self.logger.debug("Using trace ID from headers", 
                       trace_id=trace_id,
                       workflow_id=info.workflow_id)
        else:
            trace_id = info.workflow_id
            self.logger.debug("Using workflow ID as root trace ID", 
                       trace_id=trace_id,
                       workflow_id=info.workflow_id)
        
        # Store the trace ID
        self._current_trace_id = trace_id
        
        # Bind to context
        with workflow.unsafe.sandbox_unrestricted():
            try:
                self.context_bind_fn(**{self.trace_context_key: trace_id})
            except Exception as e:
                self.logger.error(f"Error setting context variable: {str(e)}")
        
        return await self.next.execute_workflow(input)

# Workflow outbound interceptor
class TraceWorkflowOutboundInterceptor(WorkflowOutboundInterceptor):
    def __init__(
        self, 
        next_interceptor: WorkflowOutboundInterceptor,
        trace_header_key: str,
        trace_context_key: str,
        get_trace_id_fn: Callable
    ):
        super().__init__(next_interceptor)
        self.trace_header_key = trace_header_key
        self.trace_context_key = trace_context_key
        self.get_trace_id_fn = get_trace_id_fn

    def _add_trace_to_headers(self, headers: dict, trace_id: Optional[str] = None) -> None:
        """Helper to add trace ID to headers"""
        if trace_id is None:
            trace_id = self.get_trace_id_fn()

        if trace_id:
            payload = workflow.payload_converter().to_payload(trace_id)
            headers[self.trace_header_key] = payload

    def start_activity(self, input: StartActivityInput) -> Any:
        self._add_trace_to_headers(input.headers)
        return self.next.start_activity(input)
    
    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        if input.parent_close_policy == workflow.ParentClosePolicy.ABANDON:
            self._add_trace_to_headers(input.headers, input.id)
        elif input.memo and "trace_id" in input.memo:
            self._add_trace_to_headers(input.headers, input.memo["trace_id"])
        else:
            self._add_trace_to_headers(input.headers)
        return await self.next.start_child_workflow(input)
    
    def start_local_activity(self, input: StartLocalActivityInput) -> Any:
        self._add_trace_to_headers(input.headers)
        return self.next.start_local_activity(input)
    
    async def signal_child_workflow(self, input: SignalChildWorkflowInput) -> None:
        self._add_trace_to_headers(input.headers)
        return await self.next.signal_child_workflow(input)
    
    async def signal_external_workflow(self, input: SignalExternalWorkflowInput) -> None:
        self._add_trace_to_headers(input.headers)
        return await self.next.signal_external_workflow(input)

# Main interceptor
class TraceInterceptor(Interceptor):
    """
    Configurable trace interceptor that propagates a trace ID across Temporal boundaries.
    
    This interceptor can be configured with custom header and context keys and a logging
    implementation, making it reusable across different codebases.
    """
    
    def __init__(
        self, 
        trace_header_key: str,
        trace_context_key: str,
        logger_module: Any,
        context_bind_fn: Callable,
    ):
        """
        Initialize the trace interceptor with configurable parameters.
        
        Args:
            trace_header_key: Header key used to propagate the trace ID
            trace_context_key: Context key used to store the trace ID
            logger_module: Logger to use for logging (must support debug method)
            context_bind_fn: Function to bind context variables
        """
        self.trace_header_key = trace_header_key
        self.trace_context_key = trace_context_key
        self.logger = logger_module.get_logger(__name__)
        self.context_bind_fn = context_bind_fn
    
    def bind_trace_context(self, trace_id: str) -> None:
        """Helper method to manually bind trace context.
        
        Call this method to set trace context in client-side code.
        """
        self.context_bind_fn(**{self.trace_context_key: trace_id})

    @staticmethod
    def generate_trace_id() -> str:
        """Generate a new trace ID."""
        return str(uuid.uuid4())
        
    def intercept_activity(self, next: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        return TraceActivityInterceptor(
            next,
            self.trace_header_key,
            self.trace_context_key,
            self.context_bind_fn
        )
    
    def workflow_interceptor_class(self, input: WorkflowInterceptorClassInput) -> Type[WorkflowInboundInterceptor]:
        def interceptor_creator(next_interceptor):
            return TraceWorkflowInboundInterceptor(
                next_interceptor,
                self.trace_header_key,
                self.trace_context_key,
                self.context_bind_fn,
                self.logger
            )
        return interceptor_creator