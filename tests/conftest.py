from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from zamp_public_workflow_sdk.temporal.models.temporal_models import \
    WorkflowExecutionStatus
from zamp_public_workflow_sdk.temporal.temporal_worker import (
    Activity, TemporalWorkerConfig, Workflow)


@pytest.fixture
def mock_workflow_execution():
    """Mock workflow execution details"""
    return MagicMock(
        id="mock-workflow-id",
        run_id="mock-run-id",
        workflow_type="JokeWorkflow",
        task_queue="mock-queue",
        status=WorkflowExecutionStatus.RUNNING,
        start_time="2024-01-01",
        close_time=None,
        execution_time="2024-01-01",
        history_length=10,
        search_attributes={},
    )


@pytest.fixture
def mock_workflow_handle(mock_workflow_execution):
    """Mock workflow handle with common operations"""
    handle = AsyncMock(spec=WorkflowHandle)

    # Start workflow operations
    handle.result_run_id = "mock-run-id"
    handle.result = AsyncMock(return_value="mock-workflow-result")
    handle.query = AsyncMock(return_value="mock-query-result")
    handle.signal = AsyncMock(return_value=None)
    handle.cancel = AsyncMock(return_value=None)
    handle.terminate = AsyncMock(return_value=None)
    handle.describe = AsyncMock(return_value=mock_workflow_execution)
    handle.fetch_history = AsyncMock(
        return_value=MagicMock(to_json_dict=lambda: [{"event": "WorkflowStarted"}])
    )

    return handle


@pytest.fixture
def mock_temporal_client(mock_workflow_handle):
    """Mock Temporal client with all operations"""
    client = AsyncMock(spec=Client)

    async def mock_start_workflow(*args, **kwargs):
        return mock_workflow_handle

    client.start_workflow = AsyncMock(side_effect=mock_start_workflow)

    async def mock_execute_workflow(*args, **kwargs):
        return "mock-execution-result"

    client.execute_workflow = AsyncMock(side_effect=mock_execute_workflow)

    def mock_get_workflow_handle(*args, **kwargs):
        return mock_workflow_handle

    client.get_workflow_handle = MagicMock(side_effect=mock_get_workflow_handle)

    async def mock_list_workflows(*args, **kwargs):
        workflows = [await mock_workflow_handle.describe()]
        for w in workflows:
            yield w

    client.list_workflows = mock_list_workflows

    async def mock_query_workflow(*args, **kwargs):
        return "mock-query-result"

    client.query_workflow = AsyncMock(side_effect=mock_query_workflow)

    async def mock_signal_workflow(*args, **kwargs):
        return None

    client.signal_workflow = AsyncMock(side_effect=mock_signal_workflow)

    async def mock_cancel_workflow(*args, **kwargs):
        return None

    client.cancel_workflow = AsyncMock(side_effect=mock_cancel_workflow)

    async def mock_terminate_workflow(*args, **kwargs):
        return None

    client.terminate_workflow = AsyncMock(side_effect=mock_terminate_workflow)

    return client


@pytest.fixture
def temporal_service(mock_temporal_client):
    """Create TemporalService with mocked client"""
    from zamp_public_workflow_sdk.temporal.temporal_client import \
        TemporalClient
    from zamp_public_workflow_sdk.temporal.temporal_service import \
        TemporalService

    temporal_client = TemporalClient(mock_temporal_client)
    return TemporalService(temporal_client)


@pytest.fixture
def mock_activity():
    async def sample_activity():
        return "activity result"

    return Activity(name="sample_activity", func=sample_activity)


@pytest.fixture
def mock_workflow():
    class SampleWorkflow:
        @staticmethod
        async def run():
            return "workflow result"

    return Workflow(name="sample_workflow", workflow=SampleWorkflow)


@pytest.fixture
def mock_worker_config(mock_activity, mock_workflow):
    return TemporalWorkerConfig(
        task_queue="test-queue",
        activities=[mock_activity],
        workflows=[mock_workflow],
        register_tasks=True,
        max_concurrent_activities=10,
    )


@pytest.fixture
def mock_worker(mock_temporal_client, mock_worker_config):
    """Mock Temporal worker"""
    worker = AsyncMock(spec=Worker)
    worker.run = AsyncMock()
    worker.shutdown = AsyncMock()
    worker.task_queue = mock_worker_config.task_queue
    worker._max_concurrent_activities = mock_worker_config.max_concurrent_activities
    worker._max_concurrent_workflow_tasks = (
        mock_worker_config.max_concurrent_workflow_tasks
    )
    return worker
