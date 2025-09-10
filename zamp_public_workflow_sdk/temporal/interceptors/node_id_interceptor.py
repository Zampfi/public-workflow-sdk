"""
NodeIdInterceptor for Temporal workflows and activities.

This interceptor handles node_id propagation from workflows to activities and child workflows by:
1. Extracting node_id from the first argument passed to activities/child workflows
2. Adding it to headers for visibility in execution history
3. Removing the node_id dict from args for clean execution

All processing is done in the WorkflowOutboundInterceptor, eliminating the need for an ActivityInboundInterceptor.
"""

from typing import Any, Callable, Type

from temporalio import workflow
from temporalio.worker import (
    Interceptor,
    StartActivityInput,
    StartChildWorkflowInput,
    WorkflowOutboundInterceptor,
)
# Constants
NODE_ID_HEADER_KEY = "node_id"
TEMPORAL_NODE_ID_KEY = "__temporal_node_id"

class NodeIdWorkflowOutboundInterceptor(WorkflowOutboundInterceptor):
    """Workflow outbound interceptor that handles node_id for activities and child workflows."""
    
    def __init__(
        self,
        next_interceptor: WorkflowOutboundInterceptor,
        node_id_header_key: str,
    ):
        super().__init__(next_interceptor)
        self.node_id_header_key = NODE_ID_HEADER_KEY
    
    def _extract_node_id_from_args(self, args: tuple) -> str:
        """Extract node_id from activity arguments."""
        for arg in args:
            # Check if arg is the node_id dict: {"__temporal_node_id": "value"}
            if isinstance(arg, dict) and TEMPORAL_NODE_ID_KEY in arg and len(arg) == 1:
                return arg[TEMPORAL_NODE_ID_KEY]
        return None
    
    def _add_node_id_to_headers(self, input: Any, node_id: str) -> None:
        """Add node_id to activity headers for ActivityInboundInterceptor to read."""
        if node_id:
            payload = workflow.payload_converter().to_payload(node_id)
            input.headers[NODE_ID_HEADER_KEY] = payload

    def _add_node_id_to_child_workflow_headers(self, input: StartChildWorkflowInput, node_id: str) -> None:
        """Add node_id to child workflow headers for visibility in execution history."""
        if node_id:
            payload = workflow.payload_converter().to_payload(node_id)
            if not hasattr(input, 'headers') or input.headers is None:
                input.headers = {}
            input.headers[NODE_ID_HEADER_KEY] = payload

    def _filter_node_id_from_args(self, args: tuple) -> tuple:
        """
        Remove '__temporal_node_id' dict from arguments.
        
        Args:
            args: Tuple of arguments that may contain node_id dict
            
        Returns:
            Filtered tuple with node_id dict removed
        """
        if not args:
            return args
            
        filtered_args = []
        for arg in args:
            # Skip the node_id dict: {"__temporal_node_id": "value"}
            if isinstance(arg, dict) and TEMPORAL_NODE_ID_KEY in arg and len(arg) == 1:
                continue
            filtered_args.append(arg)
        return tuple(filtered_args)
   
    def start_activity(self, input: StartActivityInput) -> Any:
        """Extract node_id from args, add to headers, and remove from args for clean Temporal UI."""        
        node_id = self._extract_node_id_from_args(input.args)
        if node_id:
            self._add_node_id_to_headers(input, node_id)
            input.args = self._filter_node_id_from_args(input.args)
        
        return self.next.start_activity(input)
    
    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        """Extract node_id from args, add to headers, and remove from args for clean Temporal UI."""
        node_id = self._extract_node_id_from_args(input.args)
        if node_id:
            self._add_node_id_to_child_workflow_headers(input, node_id)
            input.args = self._filter_node_id_from_args(input.args)
        
        return await self.next.start_child_workflow(input)


class NodeIdInterceptor(Interceptor):
    """
    Interceptor that handles node_id propagation from workflows to activities and child workflows.
    
    The node_id is passed as the first argument to execute_activity/execute_child_workflow in the format:
    {"__temporal_node_id": "action_name#instance"}
    
    This interceptor uses WorkflowOutboundInterceptor to:
    1. Extract node_id from args
    2. Add node_id to headers for visibility in Temporal UI
    3. Remove node_id dict from args for clean execution
    """
    
    def __init__(
        self,
        node_id_header_key: str = NODE_ID_HEADER_KEY,
        logger_module=None,
    ):
        """
        Initialize the node_id interceptor.
        
        Args:
            node_id_header_key: Key to use for node_id in headers
            logger_module: Logger module (for compatibility with other interceptors)
        """
        self.node_id_header_key = node_id_header_key
        self.logger_module = logger_module

    def workflow_interceptor_class(self, input: Any) -> Any:
        """Create a minimal workflow interceptor that only sets up the outbound interceptor."""
        node_id_header_key = self.node_id_header_key
        
        from temporalio.worker import WorkflowInboundInterceptor
        
        class MinimalInboundInterceptor(WorkflowInboundInterceptor):
            """Minimal inbound interceptor that only wraps the outbound."""
            def init(self, outbound: WorkflowOutboundInterceptor) -> None:
                super().init(NodeIdWorkflowOutboundInterceptor(outbound, node_id_header_key))
        
        return MinimalInboundInterceptor

