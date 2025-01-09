from temporalio.client import Client

from zamp_public_workflow_sdk.temporal.models.temporal_models import (
    CancelWorkflowParams, CancelWorkflowResponse, ErrorResponse,
    GetWorkflowDetailsParams, ListWorkflowParams, QueryWorkflowParams,
    QueryWorkflowResponse, RunWorkflowParams, RunWorkflowResponse,
    SignalWorkflowParams, SignalWorkflowResponse, TerminateWorkflowParams,
    TerminateWorkflowResponse, WorkflowDetailsResponse, WorkflowResponse)


class TemporalClient:
    def __init__(self, client: Client):
        self.client = client

    async def start_async_workflow(self, params: RunWorkflowParams) -> RunWorkflowResponse:
        """Start a workflow asynchronously"""
        try:
            handle = await self.client.start_workflow(
                params.workflow,
                arg=params.arg,
                id=params.id,
                task_queue=params.task_queue,
                execution_timeout=params.execution_timeout,
                run_timeout=params.run_timeout,
                task_timeout=params.task_timeout,
                id_reuse_policy=params.id_reuse_policy,
                id_conflict_policy=params.id_conflict_policy,
                retry_policy=params.retry_policy,
                cron_schedule=params.cron_schedule,
                memo=params.memo,
                search_attributes=params.search_attributes,
                start_delay=params.start_delay,
                start_signal=params.start_signal,
                start_signal_args=params.start_signal_args,
                rpc_metadata=params.rpc_metadata,
                rpc_timeout=params.rpc_timeout,
                request_eager_start=params.request_eager_start
            )
            return RunWorkflowResponse(
                run_id=handle.result_run_id,
                result=None
            )
        except Exception as e:
            return RunWorkflowResponse(
                error=ErrorResponse(
                    message=str(e),
                    internal_error={"exception": str(type(e))}
                )
            )

    async def start_sync_workflow(self, params: RunWorkflowParams) -> RunWorkflowResponse:
        """Start a workflow and wait for its completion"""
        try:
            result = await self.client.execute_workflow(
                params.workflow,
                arg=params.arg,
                id=params.id,
                task_queue=params.task_queue,
                execution_timeout=params.execution_timeout,
                run_timeout=params.run_timeout,
                task_timeout=params.task_timeout,
                id_reuse_policy=params.id_reuse_policy,
                id_conflict_policy=params.id_conflict_policy,
                retry_policy=params.retry_policy,
                cron_schedule=params.cron_schedule,
                memo=params.memo,
                search_attributes=params.search_attributes,
                start_delay=params.start_delay,
                start_signal=params.start_signal,
                start_signal_args=params.start_signal_args,
                rpc_metadata=params.rpc_metadata,
                rpc_timeout=params.rpc_timeout,
                request_eager_start=params.request_eager_start
            )
            return RunWorkflowResponse(
                result=result
            )
        except Exception as e:
            return RunWorkflowResponse(
                error=ErrorResponse(
                    message=str(e),
                    internal_error={"exception": str(type(e))}
                )
            )

    async def list_workflows(self, params: ListWorkflowParams) -> list[WorkflowResponse]:
        """List workflows based on query parameters"""
        try:
            workflows = []
            async for workflow in self.client.list_workflows(
                query=params.query,
                page_size=params.page_size,
                next_page_token=params.next_page_token
            ):
                workflows.append(WorkflowResponse.from_workflow_execution(workflow))
            return workflows
        except Exception as e:
            return [WorkflowResponse(
                workflow_id="",
                run_id="",
                workflow_type="",
                task_queue="",
                error=ErrorResponse(
                    message=str(e),
                    internal_error={"exception": str(type(e))}
                )
            )]

    async def get_workflow_details(self, params: GetWorkflowDetailsParams) -> WorkflowDetailsResponse:
        """Get details of a specific workflow"""
        try:
            handle = self.client.get_workflow_handle(
                workflow_id=params.workflow_id,
                run_id=params.run_id
            )
            desc = await handle.describe()
            history = await handle.fetch_history()

            return WorkflowDetailsResponse(
                details=WorkflowResponse.from_workflow_execution(desc),
                history=history.to_json_dict()
            )
        except Exception as e:
            return WorkflowDetailsResponse(
                details=WorkflowResponse(
                    workflow_id=params.workflow_id,
                    run_id=params.run_id or "",
                    workflow_type="",
                    task_queue=""
                ),
                history=[],
                error=ErrorResponse(
                    message=str(e),
                    internal_error={"exception": str(type(e))}
                )
            )

    async def query_workflow(self, params: QueryWorkflowParams) -> QueryWorkflowResponse:
        """Query a workflow"""
        try:
            handle = self.client.get_workflow_handle(
                workflow_id=params.workflow_id,
                run_id=params.run_id
            )
            result = await handle.query(params.query, *([params.args] if params.args else []))
            return QueryWorkflowResponse(response=result)
        except Exception as e:
            return QueryWorkflowResponse(
                error=ErrorResponse(
                    message=str(e),
                    internal_error={"exception": str(type(e))}
                )
            )

    async def signal_workflow(self, params: SignalWorkflowParams) -> SignalWorkflowResponse:
        """Send a signal to a workflow"""
        try:
            handle = self.client.get_workflow_handle(
                workflow_id=params.workflow_id,
                run_id=params.run_id
            )
            await handle.signal(params.signal_name, *([params.args] if params.args else []))
            return SignalWorkflowResponse()
        except Exception as e:
            return SignalWorkflowResponse(
                error=ErrorResponse(
                    message=str(e),
                    internal_error={"exception": str(type(e))}
                )
            )

    async def cancel_workflow(self, params: CancelWorkflowParams) -> CancelWorkflowResponse:
        """Cancel a workflow execution"""
        try:
            handle = self.client.get_workflow_handle(
                workflow_id=params.workflow_id,
                run_id=params.run_id
            )
            await handle.cancel()
            return CancelWorkflowResponse()
        except Exception as e:
            return CancelWorkflowResponse(
                error=ErrorResponse(
                    message=str(e),
                    internal_error={"exception": str(type(e))}
                )
            )

    async def terminate_workflow(self, params: TerminateWorkflowParams) -> TerminateWorkflowResponse:
        """Terminate a workflow execution"""
        try:
            handle = self.client.get_workflow_handle(
                workflow_id=params.workflow_id,
                run_id=params.run_id,
            )
            await handle.terminate(reason=params.reason)
            return TerminateWorkflowResponse()
        except Exception as e:
            return TerminateWorkflowResponse(
                error=ErrorResponse(
                    message=str(e),
                    internal_error={"exception": str(type(e))}
                )
            )
