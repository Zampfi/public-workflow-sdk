import concurrent
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Callable, Sequence

from temporalio.worker import Worker, UnsandboxedWorkflowRunner
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions
from zamp_public_workflow_sdk.temporal.temporal_client import TemporalClient


@dataclass
class Activity:
    name: str
    func: Callable

@dataclass
class Workflow:
    name: str
    workflow: type

@dataclass
class TemporalWorkerConfig:
    task_queue: str
    register_tasks: bool = False
    activities: Sequence[Activity] = field(default_factory=list)
    workflows: Sequence[Workflow] = field(default_factory=list)
    activity_executor: concurrent.futures.Executor | None = None
    workflow_task_executor: concurrent.futures.ThreadPoolExecutor | None = None
    max_cached_workflows: int = 1000
    max_concurrent_workflow_tasks: int | None = None
    max_concurrent_activities: int | None = None
    max_concurrent_local_activities: int | None = None
    max_concurrent_workflow_task_polls: int = 5
    nonsticky_to_sticky_poll_ratio: float = 0.2
    max_concurrent_activity_task_polls: int = 5
    no_remote_activities: bool = False
    sticky_queue_schedule_to_start_timeout: timedelta = timedelta(seconds=10)
    max_heartbeat_throttle_interval: timedelta = timedelta(seconds=60)
    default_heartbeat_throttle_interval: timedelta = timedelta(seconds=30)
    max_activities_per_second: float | None = None
    max_task_queue_activities_per_second: float | None = None
    graceful_shutdown_timeout: timedelta = timedelta()
    debug_mode: bool = False
    interceptors: Sequence[object] = field(default_factory=list)
    disable_sandbox: bool = False

class TemporalWorker(Worker):
    def __init__(self, temporal_client: TemporalClient, config: TemporalWorkerConfig):
        self.activities = config.activities
        self.workflows = config.workflows
        self.register_tasks = config.register_tasks

        activities = [activity.func for activity in self.activities]
        workflows = [workflow.workflow for workflow in self.workflows]
        
        additional_options = {}
        if config.disable_sandbox:
            additional_options["workflow_runner"] = UnsandboxedWorkflowRunner()
        else:
            additional_options["workflow_runner"] = SandboxedWorkflowRunner(
                restrictions=SandboxRestrictions.default.with_passthrough_modules(
                    "sentry_sdk",
                    "structlog",
                )
            )
        super().__init__(
            client=temporal_client.client,
            task_queue=config.task_queue,
            activities=activities,
            workflows=workflows,
            activity_executor=config.activity_executor,
            workflow_task_executor=config.workflow_task_executor,
            max_cached_workflows=config.max_cached_workflows,
            max_concurrent_workflow_tasks=config.max_concurrent_workflow_tasks,
            max_concurrent_activities=config.max_concurrent_activities,
            max_concurrent_local_activities=config.max_concurrent_local_activities,
            max_concurrent_workflow_task_polls=config.max_concurrent_workflow_task_polls,
            nonsticky_to_sticky_poll_ratio=config.nonsticky_to_sticky_poll_ratio,
            max_concurrent_activity_task_polls=config.max_concurrent_activity_task_polls,
            no_remote_activities=config.no_remote_activities,
            sticky_queue_schedule_to_start_timeout=config.sticky_queue_schedule_to_start_timeout,
            max_heartbeat_throttle_interval=config.max_heartbeat_throttle_interval,
            default_heartbeat_throttle_interval=config.default_heartbeat_throttle_interval,
            max_activities_per_second=config.max_activities_per_second,
            max_task_queue_activities_per_second=config.max_task_queue_activities_per_second,
            graceful_shutdown_timeout=config.graceful_shutdown_timeout,
            debug_mode=config.debug_mode,
            interceptors=config.interceptors,
            **additional_options
        )

    def _register_tasks(self):
        pass

    async def run(self):
        if self.register_tasks:
            self.register_tasks()
        await super().run()
