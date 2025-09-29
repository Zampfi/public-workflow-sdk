from __future__ import annotations

from datetime import timedelta

import pytest

from zamp_public_workflow_sdk.temporal.models.temporal_models import (
    CancelWorkflowParams, GetWorkflowDetailsParams, ListWorkflowParams,
    QueryWorkflowParams, RunWorkflowParams, SignalWorkflowParams,
    TerminateWorkflowParams)
from zamp_public_workflow_sdk.temporal.temporal_service import (TemporalClientConfig,
                                                        TemporalService)


@pytest.fixture
def service_config():
    return TemporalClientConfig(
        host="test-host:7233",
        namespace="test-namespace",
        is_cloud=False
    )

@pytest.mark.asyncio
async def test_service_initialization(temporal_service):
    assert isinstance(temporal_service, TemporalService)
    assert temporal_service.workflow_manager is not None

@pytest.mark.asyncio
async def test_start_async_workflow(temporal_service, mock_workflow_handle):
    response = await temporal_service.start_async_workflow(
        RunWorkflowParams(
            workflow="TestWorkflow",
            id="test-id",
            task_queue="test-queue"
        )
    )
    assert response.error is None
    assert response.run_id == "mock-run-id"

@pytest.mark.asyncio
async def test_start_sync_workflow(temporal_service):
    response = await temporal_service.start_sync_workflow(
        RunWorkflowParams(
            workflow="TestWorkflow",
            id="test-id",
            task_queue="test-queue"
        )
    )
    assert response.error is None
    assert response.result == "mock-execution-result"

@pytest.mark.asyncio
async def test_list_workflows(temporal_service):
    response = await temporal_service.list_workflows(
        ListWorkflowParams(
            query="WorkflowType='TestWorkflow'",
            page_size=10
        )
    )
    assert len(response) > 0
    assert response[0].workflow_type == "JokeWorkflow"

@pytest.mark.asyncio
async def test_get_workflow_details(temporal_service):
    response = await temporal_service.get_workflow_details(
        GetWorkflowDetailsParams(
            workflow_id="test-id"
        )
    )
    assert response.error is None
    assert response.details.workflow_id == "mock-workflow-id"
    assert isinstance(response.history, list)

@pytest.mark.asyncio
async def test_query_workflow(temporal_service):
    response = await temporal_service.query_workflow(
        QueryWorkflowParams(
            workflow_id="test-id",
            query="test_query"
        )
    )
    assert response.error is None
    assert response.response == "mock-query-result"

@pytest.mark.asyncio
async def test_signal_workflow(temporal_service):
    response = await temporal_service.signal_workflow(
        SignalWorkflowParams(
            workflow_id="test-id",
            signal_name="test_signal"
        )
    )
    assert response.error is None

@pytest.mark.asyncio
async def test_cancel_workflow(temporal_service):
    response = await temporal_service.cancel_workflow(
        CancelWorkflowParams(
            workflow_id="test-id"
        )
    )
    assert response.error is None

@pytest.mark.asyncio
async def test_terminate_workflow(temporal_service):
    response = await temporal_service.terminate_workflow(
        TerminateWorkflowParams(
            workflow_id="test-id",
            reason="test reason"
        )
    )
    assert response.error is None
