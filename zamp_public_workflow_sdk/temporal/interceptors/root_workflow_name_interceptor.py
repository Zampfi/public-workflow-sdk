"""
RootWorkflowNameInterceptor for Temporal workflows.

This interceptor handles root_workflow_name propagation from parent workflows to child workflows by:
1. Extracting root_workflow_name from args passed to child workflows
2. Adding it to headers for inheritance by child workflows
3. Removing the root_workflow_name dict from args for clean execution
"""

from typing import Any

from temporalio import workflow
from temporalio.worker import (
    Interceptor,
    StartChildWorkflowInput,
    WorkflowInboundInterceptor,
    WorkflowOutboundInterceptor,
)

# Constants
ROOT_WORKFLOW_NAME_HEADER_KEY = "root_workflow_name"
TEMPORAL_ROOT_WORKFLOW_NAME_KEY = "__temporal_root_workflow_name"


class RootWorkflowNameWorkflowOutboundInterceptor(WorkflowOutboundInterceptor):
    """Workflow outbound interceptor that handles root_workflow_name for child workflows."""

    def __init__(
        self,
        next_interceptor: WorkflowOutboundInterceptor,
    ):
        super().__init__(next_interceptor)

    def _check_root_workflow_name_present(self, arg: Any) -> bool:
        """Check if argument is a valid root_workflow_name dict."""
        return isinstance(arg, dict) and TEMPORAL_ROOT_WORKFLOW_NAME_KEY in arg and len(arg) == 1

    def _extract_root_workflow_name_from_args(self, args: tuple) -> str | None:
        """Extract root_workflow_name from arguments."""
        for arg in args:
            if self._check_root_workflow_name_present(arg):
                return arg[TEMPORAL_ROOT_WORKFLOW_NAME_KEY]
        return None

    def _add_to_headers(self, input: Any, value: str) -> None:
        """Add root_workflow_name to headers for inheritance by child workflows."""
        if value:
            payload = workflow.payload_converter().to_payload(value)
            if not hasattr(input, "headers") or input.headers is None:
                input.headers = {}
            input.headers[ROOT_WORKFLOW_NAME_HEADER_KEY] = payload

    def _filter_root_workflow_name_from_args(self, args: tuple) -> tuple:
        """
        Remove '__temporal_root_workflow_name' dict from arguments.

        Args:
            args: Tuple of arguments that may contain root_workflow_name dict

        Returns:
            Filtered tuple with root_workflow_name dict removed
        """
        if not args:
            return args

        filtered_args = []
        for arg in args:
            if self._check_root_workflow_name_present(arg):
                continue
            filtered_args.append(arg)
        return tuple(filtered_args)

    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        """Extract root_workflow_name from args, add to headers, and remove from args."""
        root_workflow_name = self._extract_root_workflow_name_from_args(input.args)

        if root_workflow_name:
            self._add_to_headers(input, root_workflow_name)
            input.args = self._filter_root_workflow_name_from_args(input.args)

        return await self.next.start_child_workflow(input)


class RootWorkflowNameInterceptor(Interceptor):
    """
    Interceptor that handles root_workflow_name propagation from parent workflows to child workflows.

    The root_workflow_name is passed as an argument to execute_child_workflow/start_child_workflow in the format:
    {"__temporal_root_workflow_name": "custom-workflow-name"}

    This interceptor uses WorkflowOutboundInterceptor to:
    1. Extract root_workflow_name from args
    2. Add root_workflow_name to headers for inheritance by child workflows
    3. Remove root_workflow_name dict from args for clean execution
    """

    def __init__(
        self,
        logger_module=None,
    ):
        """
        Initialize the root_workflow_name interceptor.

        Args:
            logger_module: Logger module (for compatibility with other interceptors)
        """
        self.logger_module = logger_module

    def workflow_interceptor_class(self, input: Any) -> Any:
        """Create a workflow interceptor that sets up the outbound interceptor."""

        class RootWorkflowNameWorkflowInboundInterceptor(WorkflowInboundInterceptor):
            """Workflow inbound interceptor that wraps the outbound with root_workflow_name handling."""

            def init(self, outbound: WorkflowOutboundInterceptor) -> None:
                super().init(RootWorkflowNameWorkflowOutboundInterceptor(outbound))

        return RootWorkflowNameWorkflowInboundInterceptor
