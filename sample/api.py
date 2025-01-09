import uuid
from datetime import timedelta

from temporalio.common import RetryPolicy

from sample.params import WorkflowInput
from zamp_public_workflow_sdk.temporal.models.temporal_models import *
from zamp_public_workflow_sdk.temporal.temporal_service import (TemporalClientConfig,
                                                        TemporalService)


class API:
    def __init__(self):
        self.workflow_service = TemporalService.connect()

    @staticmethod
    async def get_api_handle():
        return await TemporalService.connect(
            TemporalClientConfig(
                host="localhost:7233",
                namespace="default",
                is_cloud=True
            )
        )


async def run_workflow() -> tuple[str, str, RunWorkflowResponse]:
    api = await API.get_api_handle()
    random_uuid = uuid.uuid4()
    workflow_id = str(random_uuid)
    result = await api.start_async_workflow(
        RunWorkflowParams(
            workflow='JokeWorkflow',
            arg=WorkflowInput(
                workflow_name="joke-workflowflow-2",
                tenant_id="abc",
                context="This is a joke context"
            ),
            task_queue='joke-queue',
            id=workflow_id,
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,
                maximum_attempts=10,
                maximum_interval=timedelta(seconds=30),
                non_retryable_error_types=["NonRetryableError"]
            ),
            cron_schedule="* * * * *",
        )
    )
    return workflow_id, result.run_id, result


async def list_workflows():
    api = await API.get_api_handle()
    running = await api.list_workflows(
        ListWorkflowParams(
            query="WorkflowType = 'JokeWorkflow' ", # refer : temporal query syntax for more 
            page_size=100
        )
    )
    return running

async def get_workflow_details():
    api = await API.get_api_handle()
    result = await list_workflows()
    ans = result[0]
    workflow = await api.get_workflow_details(
        GetWorkflowDetailsParams(
            workflow_id=ans.workflow_id,
            run_id=ans.run_id
        )
    )
    return workflow

async def query_workflow():
    api = await API.get_api_handle()
    result = await list_workflows()
    ans = result[0]

    result = await api.query_workflow(
        QueryWorkflowParams(
            workflow_id=ans.workflow_id,
            run_id=ans.run_id,
            query="get_state",
            args="Write a new Joke"
        )
    )
    return result


async def signal_workflow():
    api = await API.get_api_handle()
    result = await list_workflows()
    ans = result[0]

    result = await api.signal_workflow(
        SignalWorkflowParams(
            workflow_id=ans.workflow_id,
            run_id=ans.run_id,
            signal_name="change_state",
            args="Write a new Joke"
        )
    )
    return result

async def execute_workflow():
    api = await API.get_api_handle()
    random_uuid = uuid.uuid4()
    uuid_string = str(random_uuid)

    result = await api.start_sync_workflow(
        RunWorkflowParams(
            workflow='JokeWorkflow',
            id=uuid_string,
            arg=WorkflowInput(
                workflow_name="joke-workflowflow-2",
                tenant_id="abc",
                context="This is a joke context"
            ),
            task_queue='joke-queue'
        )
    )
    return result

async def cancel_workflow():
    api = await API.get_api_handle()
    result = await list_workflows()
    ans = result[0]  # Get first workflow from list

    result = await api.cancel_workflow(
        CancelWorkflowParams(
            workflow_id=ans.workflow_id,
            run_id=ans.run_id
        )
    )
    return result

async def terminate_workflow():
    api = await API.get_api_handle()

    result = await api.terminate_workflow(
        TerminateWorkflowParams(
            workflow_id='ce3ee770-a33a-4944-b736-4a2d8fa9be05',
            run_id='cbf62062-ef05-4f50-b002-737bb4b63e26',
            reason="Testing terminate workflow"
        )
    )
    return result
