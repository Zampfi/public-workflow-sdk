"""
NodeIdInterceptor for Temporal workflows and activities.

This interceptor handles node_id propagation from workflows to activities and child workflows by:
1. Extracting node_id from the first argument passed to activities/child workflows
2. Adding it to headers for visibility in execution history
3. Removing the node_id dict from args for clean execution

All processing is done in the WorkflowOutboundInterceptor, eliminating the need for an ActivityInboundInterceptor.
"""

from typing import Any, Callable, Type, Optional

from temporalio import workflow
from temporalio.worker import (
    Interceptor,
    StartActivityInput,
    StartChildWorkflowInput,
    WorkflowOutboundInterceptor,
    WorkflowInboundInterceptor,
)
# Constants
NODE_ID_HEADER_KEY = "node_id"
TEMPORAL_NODE_ID_KEY = "__temporal_node_id"

class NodeIdWorkflowOutboundInterceptor(WorkflowOutboundInterceptor):
    """Workflow outbound interceptor that handles node_id for activities and child workflows."""
    
    def __init__(
        self,
        next_interceptor: WorkflowOutboundInterceptor,
    ):
        super().__init__(next_interceptor)
    
    def _check_temporal_node_id_present(self, arg: Any) -> bool:
        """Check if argument is a valid temporal node_id dict."""
        return isinstance(arg, dict) and TEMPORAL_NODE_ID_KEY in arg and len(arg) == 1
    
    def _extract_node_id_from_args(self, args: tuple) -> Optional[str]:
        """Extract node_id from activity arguments."""
        for arg in args:
            if self._check_temporal_node_id_present(arg):
                return arg[TEMPORAL_NODE_ID_KEY]
        return None
    
    def _add_node_id_to_activity_headers(self, input: Any, node_id: str) -> None:
        """Add node_id to headers for visibility in execution history."""
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
            if self._check_temporal_node_id_present(arg):
                continue
            filtered_args.append(arg)
        return tuple(filtered_args)
   
    def start_activity(self, input: StartActivityInput) -> Any:
        """Extract node_id from args, add to headers, and remove from args for clean Temporal UI."""        
        node_id = self._extract_node_id_from_args(input.args)
        if node_id:
            self._add_node_id_to_activity_headers(input, node_id)
            input.args = self._filter_node_id_from_args(input.args)
        
        return self.next.start_activity(input)
    
    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        """Extract node_id from args, add to headers, and remove from args for clean Temporal UI."""
        node_id = self._extract_node_id_from_args(input.args)
        if node_id:
            self._add_node_id_to_activity_headers(input, node_id)
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
        logger_module=None,
    ):
        """
        Initialize the node_id interceptor.
        
        Args:
            logger_module: Logger module (for compatibility with other interceptors)
        """
        self.logger_module = logger_module

    def workflow_interceptor_class(self, input: Any) -> Any:
        """Create a workflow interceptor that only sets up the outbound interceptor."""
        
        class NodeIdWorkflowInboundInterceptor(WorkflowInboundInterceptor):
            """Workflow inbound interceptor that wraps the outbound with node_id handling."""
            def init(self, outbound: WorkflowOutboundInterceptor) -> None:
                super().init(NodeIdWorkflowOutboundInterceptor(outbound))
        
        return NodeIdWorkflowInboundInterceptor

