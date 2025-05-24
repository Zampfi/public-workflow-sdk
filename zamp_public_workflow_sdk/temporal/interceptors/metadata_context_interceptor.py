"""
Configurable metadata context interceptor for Temporal workflows and activities.

This interceptor extracts metadata from the zamp_metadata_context field in workflow 
and activity arguments and binds them to the Python context.
"""

from typing import Any, Callable, Dict, Optional, Type

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
        return await self.next.execute_activity(input)
    
    def _bind_metadata_from_args(self, args: tuple) -> None:
        """Extract metadata context from args and bind to context"""
        # Check args for metadata context
        for arg in args:
            if isinstance(arg, dict) and METADATA_CONTEXT_FIELD in arg:
                metadata = arg.get(METADATA_CONTEXT_FIELD)
                if isinstance(metadata, dict):
                    # Bind each key-value pair to context
                    for key, value in metadata.items():
                        try:
                            self.context_bind_fn(**{key: value})
                        except Exception as e:
                            self.logger.error(f"Error binding metadata context variable {key}: {str(e)}")


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
        
        # Bind metadata to context
        with workflow.unsafe.sandbox_unrestricted():
            try:
                for key, value in self._current_metadata.items():
                    self.context_bind_fn(**{key: value})
            except Exception as e:
                self.logger.error(f"Error setting metadata context variables: {str(e)}")
        
        return await self.next.execute_workflow(input)
    
    def _extract_metadata_from_args(self, args: tuple) -> None:
        """Extract metadata context from args and store it"""
        # Check args for metadata context
        for arg in args:
            if isinstance(arg, dict) and METADATA_CONTEXT_FIELD in arg:
                metadata = arg.get(METADATA_CONTEXT_FIELD)
                if isinstance(metadata, dict):
                    self._current_metadata = metadata
                    self.logger.debug("Found metadata context in workflow args", 
                                    metadata=metadata)
                    break


# Workflow outbound interceptor
class MetadataContextWorkflowOutboundInterceptor(WorkflowOutboundInterceptor):
    def __init__(
        self,
        next_interceptor: WorkflowOutboundInterceptor,
        get_metadata_fn: Callable,
    ):
        super().__init__(next_interceptor)
        self.get_metadata_fn = get_metadata_fn

    def _add_metadata_to_args(self, args: tuple) -> tuple:
        """Add metadata context to args if needed"""
        metadata = self.get_metadata_fn()
        if not metadata:
            return args
            
        # If there's already a dict with the metadata field, update it
        for i, arg in enumerate(args):
            if isinstance(arg, dict) and METADATA_CONTEXT_FIELD in arg:
                new_args = list(args)
                new_args[i][METADATA_CONTEXT_FIELD].update(metadata)
                return tuple(new_args)
        
        # Otherwise, add a new dict with the metadata field
        return args + (({METADATA_CONTEXT_FIELD: metadata},),)

    def start_activity(self, input: StartActivityInput) -> Any:
        # Add metadata context to activity args
        input.args = self._add_metadata_to_args(input.args)
        return self.next.start_activity(input)
    
    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        # Add metadata context to child workflow args
        input.args = self._add_metadata_to_args(input.args)
        return await self.next.start_child_workflow(input)
    
    def start_local_activity(self, input: StartLocalActivityInput) -> Any:
        # Add metadata context to local activity args
        input.args = self._add_metadata_to_args(input.args)
        return self.next.start_local_activity(input)
    
    async def signal_child_workflow(self, input: SignalChildWorkflowInput) -> None:
        # Add metadata context to signal args
        input.args = self._add_metadata_to_args(input.args)
        return await self.next.signal_child_workflow(input)
    
    async def signal_external_workflow(self, input: SignalExternalWorkflowInput) -> None:
        # Add metadata context to signal args
        input.args = self._add_metadata_to_args(input.args)
        return await self.next.signal_external_workflow(input)


# Main interceptor
class MetadataContextInterceptor(Interceptor):
    """
    Configurable metadata context interceptor that extracts and propagates metadata from arguments.
    
    This interceptor looks for a 'zamp_metadata_context' field in workflow and activity arguments.
    If found, it binds all key-value pairs from this field to the Python context using the
    provided context binding function.
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