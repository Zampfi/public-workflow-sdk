"""
Configurable metadata context interceptor for Temporal workflows and activities.

This interceptor extracts metadata from the zamp_metadata_context field in workflow 
and activity arguments and binds them to the Python context.
"""

from typing import Any, Callable, Dict, Type

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

# Constant for the metadata context field name
METADATA_CONTEXT_FIELD = "zamp_metadata_context"

# Activity interceptor
class MetadataContextActivityInterceptor(ActivityInboundInterceptor):
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
        # Extract metadata from args if present
        self._bind_metadata_from_args(input.args)
        
        # Also check headers for metadata (from parent workflow)
        self._bind_metadata_from_headers(input.headers)
        
        return await self.next.execute_activity(input)
    
    def _bind_metadata_from_args(self, args: tuple) -> None:
        """Extract metadata context from args and bind to context"""
        for arg in args:
            # Check if arg has zamp_metadata_context attribute
            if hasattr(arg, METADATA_CONTEXT_FIELD):
                metadata_obj = getattr(arg, METADATA_CONTEXT_FIELD)
                # Convert Pydantic model to dict
                if hasattr(metadata_obj, "dict") and callable(getattr(metadata_obj, "dict")):
                    metadata = metadata_obj.dict()
                    # Bind each key-value pair to context
                    for key, value in metadata.items():
                        try:
                            self.context_bind_fn(**{key: value})
                        except Exception as e:
                            self.logger.error(f"Error binding metadata context variable {key}: {str(e)}")
                    break  # Found metadata, no need to check other args

    def _bind_metadata_from_headers(self, headers: dict) -> None:
        """Extract metadata context from headers and bind to context"""
        if METADATA_CONTEXT_FIELD in headers:
            try:
                payload = headers.get(METADATA_CONTEXT_FIELD)
                metadata = activity.payload_converter().from_payload(payload, dict)
                # Bind each key-value pair to context
                for key, value in metadata.items():
                    try:
                        self.context_bind_fn(**{key: value})
                    except Exception as e:
                        self.logger.error(f"Error binding metadata context variable {key}: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error extracting metadata from headers: {str(e)}")


# Workflow inbound interceptor
class MetadataContextWorkflowInboundInterceptor(WorkflowInboundInterceptor):
    def __init__(
        self,
        next_interceptor: WorkflowInboundInterceptor,
        context_bind_fn: Callable,
        logger: Any,
    ):
        super().__init__(next_interceptor)
        self.context_bind_fn = context_bind_fn
        self.logger = logger
        self._current_metadata = {}

    def init(self, outbound: WorkflowOutboundInterceptor) -> None:
        self.next.init(MetadataContextWorkflowOutboundInterceptor(
            outbound,
            self.get_metadata
        ))

    def get_metadata(self) -> Dict[str, Any]:
        """Get the current metadata context."""
        return self._current_metadata

    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        # Extract metadata from args if present
        self._extract_metadata_from_args(input.args)
        
        # Also check headers for metadata (from parent workflow)
        self._extract_metadata_from_headers(input.headers)
        
        # Bind metadata to context
        if self._current_metadata:
            with workflow.unsafe.sandbox_unrestricted():
                try:
                    for key, value in self._current_metadata.items():
                        self.context_bind_fn(**{key: value})
                except Exception as e:
                    self.logger.error(f"Error setting metadata context variables: {str(e)}")
        
        return await self.next.execute_workflow(input)
    
    def _extract_metadata_from_args(self, args: tuple) -> None:
        """Extract metadata context from args and store it"""
        for arg in args:
            # Check if arg has zamp_metadata_context attribute
            if hasattr(arg, METADATA_CONTEXT_FIELD):
                metadata_obj = getattr(arg, METADATA_CONTEXT_FIELD)
                # Handle both Pydantic model and plain dict
                if hasattr(metadata_obj, "dict") and callable(getattr(metadata_obj, "dict")):
                    # It's a Pydantic model
                    metadata = metadata_obj.dict()
                    self._current_metadata = metadata
                    break
                elif isinstance(metadata_obj, dict):
                    # It's already a dictionary
                    self._current_metadata = metadata_obj
                    break

    def _extract_metadata_from_headers(self, headers: dict) -> None:
        """Extract metadata context from headers and store it"""
        if METADATA_CONTEXT_FIELD in headers:
            try:
                payload = headers.get(METADATA_CONTEXT_FIELD)
                metadata = workflow.payload_converter().from_payload(payload, dict)
                # Only use headers if we don't already have metadata from args
                if not self._current_metadata:
                    self._current_metadata = metadata
                    self.logger.debug("Found metadata context in workflow headers", metadata=metadata)
            except Exception as e:
                self.logger.error(f"Error extracting metadata from headers: {str(e)}")


# Workflow outbound interceptor
class MetadataContextWorkflowOutboundInterceptor(WorkflowOutboundInterceptor):
    def __init__(
        self,
        next_interceptor: WorkflowOutboundInterceptor,
        get_metadata_fn: Callable,
    ):
        super().__init__(next_interceptor)
        self.get_metadata_fn = get_metadata_fn

    def _add_metadata_to_headers(self, headers: dict) -> None:
        """Add metadata context to headers"""
        metadata = self.get_metadata_fn()
        if metadata:
            payload = workflow.payload_converter().to_payload(metadata)
            headers[METADATA_CONTEXT_FIELD] = payload

    def start_activity(self, input: StartActivityInput) -> Any:
        # Add metadata context to activity headers
        self._add_metadata_to_headers(input.headers)
        return self.next.start_activity(input)
    
    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        # Add metadata context to child workflow headers
        self._add_metadata_to_headers(input.headers)
        return await self.next.start_child_workflow(input)
    
    def start_local_activity(self, input: StartLocalActivityInput) -> Any:
        # Add metadata context to local activity headers
        self._add_metadata_to_headers(input.headers)
        return self.next.start_local_activity(input)
    
    async def signal_child_workflow(self, input: SignalChildWorkflowInput) -> None:
        # Add metadata context to signal headers
        self._add_metadata_to_headers(input.headers)
        return await self.next.signal_child_workflow(input)
    
    async def signal_external_workflow(self, input: SignalExternalWorkflowInput) -> None:
        # Add metadata context to signal headers
        self._add_metadata_to_headers(input.headers)
        return await self.next.signal_external_workflow(input)


# Main interceptor
class MetadataContextInterceptor(Interceptor):
    """
    Configurable metadata context interceptor that extracts and propagates metadata from arguments.
    
    This interceptor looks for a 'zamp_metadata_context' attribute in workflow and activity arguments.
    If found, it converts the Pydantic model to a dictionary and binds all key-value pairs 
    to the Python context using the provided context binding function.
    
    The metadata is automatically propagated to child workflows and activities through headers,
    so they can access the same context variables without modifying their arguments.
    
    Expected usage:
    - Arguments should be Pydantic models with a 'zamp_metadata_context' attribute
    - The 'zamp_metadata_context' should be a Pydantic model (e.g., ZampMetadataContext)
    
    This interceptor extracts metadata from incoming calls and propagates it through headers
    to child workflows/activities without modifying their arguments.
    """
    
    def __init__(
        self,
        logger_module: Any,
        context_bind_fn: Callable,
    ):
        """
        Initialize the metadata context interceptor with configurable parameters.
        
        Args:
            logger_module: Logger to use for logging (must support debug and error methods)
            context_bind_fn: Function to bind context variables
        """
        self.logger = logger_module.get_logger(__name__)
        self.context_bind_fn = context_bind_fn
    
    def intercept_activity(self, next: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        return MetadataContextActivityInterceptor(
            next,
            self.context_bind_fn,
            self.logger
        )
    
    def workflow_interceptor_class(self, input: WorkflowInterceptorClassInput) -> Type[WorkflowInboundInterceptor]:
        def interceptor_creator(next_interceptor):
            return MetadataContextWorkflowInboundInterceptor(
                next_interceptor,
                self.context_bind_fn,
                self.logger
            )
        return interceptor_creator 