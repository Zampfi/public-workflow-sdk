"""
Configurable Sentry interceptor for Temporal workflows and activities.

This interceptor captures workflow and activity failures and reports them to Sentry.
"""

import traceback
from typing import Any, Callable, Optional, Type

from temporalio.worker import (
    ActivityInboundInterceptor,
    ActivityOutboundInterceptor,
    ExecuteActivityInput,
    ExecuteWorkflowInput,
    Interceptor,
    WorkflowInboundInterceptor,
    WorkflowOutboundInterceptor,
    WorkflowInterceptorClassInput,
    StartChildWorkflowInput,
)
from temporalio import workflow
import time

with workflow.unsafe.imports_passed_through():
    from sentry_sdk import capture_exception, push_scope, init


class SentryActivityInboundInterceptor(ActivityInboundInterceptor):
    """Activity inbound interceptor that reports failures to Sentry."""

    def __init__(
        self,
        next_interceptor: ActivityInboundInterceptor,
        logger: Any,
        additional_context_fn: Optional[Callable] = None,
    ):
        self.next = next_interceptor
        self.logger = logger
        self.additional_context_fn = additional_context_fn

    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        """Execute activity and report failures to Sentry."""
        try:
            return await self.next.execute_activity(input)
        except Exception as e:
            with push_scope() as scope:
                activity_name = input.fn.__name__
                # Set activity-specific tags
                scope.set_tag("activity.name", activity_name)
                
                # Add detailed context
                context = {
                    "name": activity_name,
                    "headers": dict(input.headers),
                    "args": str(input.args),
                }

                # Add any additional context if provided
                if self.additional_context_fn:
                    additional_context = self.additional_context_fn(input)
                    context.update(additional_context)
                
                scope.set_context("activity_details", context)
                try:
                    capture_exception(e)
                except Exception as e:
                    self.logger.error(
                        "Sentry captured failed",
                        activity_name=activity_name,
                        error=str(e),
                    )
            raise


class SentryActivityOutboundInterceptor(ActivityOutboundInterceptor):
    """Activity outbound interceptor that reports failures to Sentry."""

    def __init__(
        self,
        next_interceptor: ActivityOutboundInterceptor,
        logger: Any,
        additional_context_fn: Optional[Callable] = None,
    ):
        self.next = next_interceptor
        self.logger = logger
        self.additional_context_fn = additional_context_fn

    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        """Execute activity and report failures to Sentry."""
        try:
            return await self.next.execute_activity(input)
        except Exception as e:
            with push_scope() as scope:
                activity_name = input.fn.__name__
                # Set activity-specific tags
                scope.set_tag("activity.name", activity_name)
                scope.set_tag("activity.direction", "outbound")
                
                # Add detailed context
                context = {
                    "name": activity_name,
                    "headers": dict(input.headers),
                    "args": str(input.args),
                    "direction": "outbound",
                }

                # Add any additional context if provided
                if self.additional_context_fn:
                    additional_context = self.additional_context_fn(input)
                    context.update(additional_context)
                
                scope.set_context("activity_details", context)
                try:
                    capture_exception(e)
                except Exception as e:
                    self.logger.error(
                        "Sentry captured failed",
                        activity_name=activity_name,
                        error=str(e),
                    )
            raise


class SentryWorkflowInboundInterceptor(WorkflowInboundInterceptor):
    """Workflow inbound interceptor that reports failures to Sentry."""

    def __init__(
        self,
        next_interceptor: WorkflowInboundInterceptor,
        logger: Any,
        additional_context_fn: Optional[Callable] = None,
    ):
        self.next = next_interceptor
        self.logger = logger
        self.additional_context_fn = additional_context_fn

    def init(self, outbound: WorkflowOutboundInterceptor) -> None:
        """Initialize with outbound interceptor."""
        self.next.init(SentryWorkflowOutboundInterceptor(
            outbound,
            self.logger,
            self.additional_context_fn,
        ))

    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        """Execute workflow and report failures to Sentry."""
        try:
            return await self.next.execute_workflow(input)
        except Exception as e:
            with push_scope() as scope:
                workflow_name = input.type.__name__
                # Set workflow-specific tags
                scope.set_tag("workflow.type", workflow_name)
                scope.set_tag("workflow.direction", "inbound")
                
                # Add detailed context
                context = {
                    "type": workflow_name,
                    "headers": dict(input.headers),
                    "args": str(input.args),
                    "direction": "inbound",
                }

                # Add any additional context if provided
                if self.additional_context_fn:
                    additional_context = self.additional_context_fn(input)
                    context.update(additional_context)
                
                scope.set_context("workflow_details", context)
                try:
                    capture_exception(e)
                except Exception as e:
                    self.logger.error(
                        "Sentry captured failed",
                        workflow_name=workflow_name,
                        error=str(e),
                    )
            raise

    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        """Execute child workflow and report failures to Sentry."""
        try:
            return await self.next.start_child_workflow(input)
        except Exception as e:
            with push_scope() as scope:
                # Set workflow-specific tags
                scope.set_tag("workflow.type", input.workflow)
                scope.set_tag("workflow.direction", "child_inbound")
                
                # Add detailed context
                context = {
                    "type": input.workflow,
                    "workflow_id": input.id,
                    "task_queue": input.task_queue,
                    "headers": dict(input.headers),
                    "args": str(input.args),
                    "direction": "child_inbound",
                    "cron_schedule": input.cron_schedule,
                    "execution_timeout": str(input.execution_timeout) if input.execution_timeout else None,
                    "run_timeout": str(input.run_timeout) if input.run_timeout else None,
                }

                # Add any additional context if provided
                if self.additional_context_fn:
                    additional_context = self.additional_context_fn(input)
                    context.update(additional_context)
                
                scope.set_context("child_workflow_details", context)
                try:
                    capture_exception(e)
                except Exception as e:
                    self.logger.error(
                        "Sentry captured failed",
                        error=str(e),
                    )
            raise


class SentryWorkflowOutboundInterceptor(WorkflowOutboundInterceptor):
    """Workflow outbound interceptor that reports failures to Sentry."""

    def __init__(
        self,
        next_interceptor: WorkflowOutboundInterceptor,
        logger: Any,
        additional_context_fn: Optional[Callable] = None,
    ):
        self.next = next_interceptor
        self.logger = logger
        self.additional_context_fn = additional_context_fn

    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        """Execute workflow and report failures to Sentry."""
        try:
            return await self.next.execute_workflow(input)
        except Exception as e:
            with push_scope() as scope:
                workflow_name = input.type.__name__
                # Set workflow-specific tags
                scope.set_tag("workflow.type", workflow_name)
                scope.set_tag("workflow.direction", "outbound")
                
                # Add detailed context
                context = {
                    "type": workflow_name,
                    "headers": dict(input.headers),
                    "args": str(input.args),
                    "direction": "outbound",
                }

                # Add any additional context if provided
                if self.additional_context_fn:
                    additional_context = self.additional_context_fn(input)
                    context.update(additional_context)
                
                scope.set_context("workflow_details", context)
                try:
                    capture_exception(e)
                except Exception as e:
                    self.logger.error(
                        "Sentry captured failed",
                        workflow_name=workflow_name,
                        error=str(e),
                    )
            raise

    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        """Execute child workflow and report failures to Sentry."""
        try:
            return await self.next.start_child_workflow(input)
        except Exception as e:
            with push_scope() as scope:
                # Set workflow-specific tags
                scope.set_tag("workflow.type", input.workflow)
                scope.set_tag("workflow.direction", "child_outbound")
                
                # Add detailed context
                context = {
                    "type": input.workflow,
                    "workflow_id": input.id,
                    "task_queue": input.task_queue,
                    "headers": dict(input.headers),
                    "args": str(input.args),
                    "direction": "child_outbound",
                    "cron_schedule": input.cron_schedule,
                    "execution_timeout": str(input.execution_timeout) if input.execution_timeout else None,
                    "run_timeout": str(input.run_timeout) if input.run_timeout else None,
                }

                # Add any additional context if provided
                if self.additional_context_fn:
                    additional_context = self.additional_context_fn(input)
                    context.update(additional_context)
                
                scope.set_context("child_workflow_details", context)
                try:
                    capture_exception(e)
                except Exception as e:
                    self.logger.error(
                        "Sentry captured failed",
                        error=str(e),
                    )
            raise


class SentryInterceptor(Interceptor):
    """
    Configurable Sentry interceptor that captures and reports workflow and activity failures.
    
    This interceptor can be configured with custom logging implementation and additional
    context functions, making it reusable across different codebases.
    """
    
    def __init__(
        self,
        logger_module: Any,
        sentry_dsn: Optional[str] = None,
        environment: Optional[str] = None,
        additional_context_fn: Optional[Callable] = None,
        **sentry_options: Any,
    ):
        """
        Initialize the Sentry interceptor with configurable parameters.
        
        Args:
            logger_module: Logger to use for logging (must support error method)
            sentry_dsn: Optional Sentry DSN. If not provided, assumes Sentry is already initialized
            environment: Optional environment name for Sentry
            additional_context_fn: Optional function to add custom context to Sentry events
            **sentry_options: Additional options to pass to sentry_sdk.init
        """
        self.logger = logger_module.get_logger(__name__)
        self.additional_context_fn = additional_context_fn

        # Initialize Sentry if DSN is provided
        if sentry_dsn:
            init(
                dsn=sentry_dsn,
                environment=environment,
                **sentry_options,
            )

    def intercept_activity(
        self, next: ActivityInboundInterceptor
    ) -> ActivityInboundInterceptor:
        """Create activity inbound interceptor."""
        return SentryActivityInboundInterceptor(
            next,
            self.logger,
            self.additional_context_fn,
        )

    def workflow_interceptor_class(
        self, input: WorkflowInterceptorClassInput
    ) -> Type[WorkflowInboundInterceptor]:
        """Create workflow inbound interceptor class."""
        def interceptor_creator(next_interceptor):
            return SentryWorkflowInboundInterceptor(
                next_interceptor,
                self.logger,
                self.additional_context_fn,
            )
        return interceptor_creator
