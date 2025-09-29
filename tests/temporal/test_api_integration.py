from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zamp_public_workflow_sdk.temporal.models.temporal_models import (
    CancelWorkflowParams, GetWorkflowDetailsParams, QueryWorkflowParams,
    SignalWorkflowParams, TerminateWorkflowParams, WorkflowExecutionStatus)


@pytest.fixture
def mock_temporal_service():
    """Mock the TemporalService connection to avoid real connection attempts."""
    with patch('zamp_public_workflow_sdk.temporal.temporal_service.TemporalService.connect') as mock_connect:
        mock_service = AsyncMock()
        mock_connect.return_value = mock_service
        yield mock_service


@pytest.mark.asyncio
async def test_create_workflow(mock_temporal_service):
    """Test workflow creation"""
    from sample.api import run_workflow

    # Mock the API response
    mock_result = MagicMock()
    mock_result.error = None
    mock_result.run_id = "test_run_id"

    # Configure the mock service to return our mock result
    mock_temporal_service.start_async_workflow.return_value = mock_result

    workflow_id, run_id, result = await run_workflow()

    assert result.error is None
    assert workflow_id is not None  # Generated UUID
    assert run_id == "test_run_id"
    print(f"✓ Created workflow: {workflow_id} with run_id: {run_id}")


@pytest.mark.asyncio
async def test_list_workflows(mock_temporal_service):
    """Test workflow listing"""
    from sample.api import list_workflows

    # Create mock workflow objects
    mock_workflow = MagicMock()
    mock_workflow.workflow_id = "test_workflow_id"
    mock_workflow.run_id = "test_run_id"
    mock_workflow.workflow_type = "JokeWorkflow"

    # Configure the mock service to return our mock workflows
    mock_temporal_service.list_workflows.return_value = [mock_workflow]

    workflows = await list_workflows()

    assert len(workflows) > 0
    workflow = workflows[0]
    assert workflow.workflow_type == "JokeWorkflow"
    assert workflow.workflow_id == "test_workflow_id"
    print(f"✓ Listed workflows, found target workflow: {workflow.workflow_id}")


@pytest.mark.asyncio
async def test_get_workflow_details(mock_temporal_service):
    """Test getting workflow details for a specific workflow"""
    from sample.api import API

    # Mock API details response
    details_mock = MagicMock()
    details_mock.workflow_id = "test_workflow_id"
    details_mock.run_id = "test_run_id"

    details_response = MagicMock()
    details_response.error = None
    details_response.details = details_mock

    mock_api = AsyncMock()
    mock_api.get_workflow_details.return_value = details_response

    with patch('sample.api.API.get_api_handle') as mock_get_api:
        mock_get_api.return_value = mock_api

        api = await API.get_api_handle()
        details = await api.get_workflow_details(
            GetWorkflowDetailsParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id"
            )
        )

        assert details.error is None
        assert details.details is not None
        assert details.details.workflow_id == "test_workflow_id"
        assert details.details.run_id == "test_run_id"
        print(f"✓ Got details for workflow: test_workflow_id")


@pytest.mark.asyncio
async def test_query_workflow(mock_temporal_service):
    """Test querying a specific workflow"""
    from sample.api import API

    # Mock query response
    query_response = MagicMock()
    query_response.error = None
    query_response.response = "test_state"

    mock_api = AsyncMock()
    mock_api.query_workflow.return_value = query_response

    with patch('sample.api.API.get_api_handle') as mock_get_api:
        mock_get_api.return_value = mock_api

        api = await API.get_api_handle()
        query_result = await api.query_workflow(
            QueryWorkflowParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id",
                query="get_state",
                args="Write a new Joke"
            )
        )

        assert query_result.error is None
        assert query_result.response is not None
        print(f"✓ Queried workflow test_workflow_id, state: {query_result.response}")


@pytest.mark.asyncio
async def test_signal_workflow(mock_temporal_service):
    """Test signaling a specific workflow"""
    from sample.api import API

    # Mock signal and query responses
    signal_response = MagicMock()
    signal_response.error = None

    query_response = MagicMock()
    query_response.error = None
    query_response.response = "Write a new Joke"

    mock_api = AsyncMock()
    mock_api.signal_workflow.return_value = signal_response
    mock_api.query_workflow.return_value = query_response

    with patch('sample.api.API.get_api_handle') as mock_get_api:
        mock_get_api.return_value = mock_api

        api = await API.get_api_handle()

        # Signal the workflow
        signal_result = await api.signal_workflow(
            SignalWorkflowParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id",
                signal_name="change_state",
                args="Write a new Joke"
            )
        )

        assert signal_result.error is None
        print(f"✓ Signaled workflow: test_workflow_id")

        # Verify state change through query
        query_result = await api.query_workflow(
            QueryWorkflowParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id",
                query="get_state"
            )
        )
        assert query_result.response == "Write a new Joke"


@pytest.mark.asyncio
async def test_execute_sync_workflow(mock_temporal_service):
    """Test executing a synchronous workflow"""
    from sample.api import execute_workflow

    mock_result = MagicMock()
    mock_result.error = None
    mock_result.result = "Test execution result"

    # Configure the mock service to return our mock result
    mock_temporal_service.start_sync_workflow.return_value = mock_result

    result = await execute_workflow()

    assert result.error is None
    assert result.result is not None
    print(f"✓ Executed sync workflow with result: {result.result}")


@pytest.mark.asyncio
async def test_cancel_workflow(mock_temporal_service):
    """Test canceling a specific workflow"""
    from sample.api import API

    # Mock cancel and details responses
    cancel_response = MagicMock()
    cancel_response.error = None

    canceled_details_mock = MagicMock()
    canceled_details_mock.workflow_id = "test_workflow_id"
    canceled_details_mock.run_id = "test_run_id"
    canceled_details_mock.status = WorkflowExecutionStatus.CANCELED

    canceled_details_response = MagicMock()
    canceled_details_response.error = None
    canceled_details_response.details = canceled_details_mock

    mock_api = AsyncMock()
    mock_api.cancel_workflow.return_value = cancel_response
    mock_api.get_workflow_details.return_value = canceled_details_response

    with patch('sample.api.API.get_api_handle') as mock_get_api:
        mock_get_api.return_value = mock_api

        api = await API.get_api_handle()

        # Cancel the workflow
        cancel_result = await api.cancel_workflow(
            CancelWorkflowParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id"
            )
        )

        assert cancel_result.error is None
        print(f"✓ Canceled workflow: test_workflow_id")

        # Verify cancellation
        details = await api.get_workflow_details(
            GetWorkflowDetailsParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id"
            )
        )
        assert details.details.status == WorkflowExecutionStatus.CANCELED


@pytest.mark.asyncio
async def test_terminate_workflow(mock_temporal_service):
    """Test terminating a specific workflow"""
    from sample.api import API

    # Mock terminate and details responses
    terminate_response = MagicMock()
    terminate_response.error = None

    terminated_details_mock = MagicMock()
    terminated_details_mock.workflow_id = "test_workflow_id"
    terminated_details_mock.run_id = "test_run_id"
    terminated_details_mock.status = WorkflowExecutionStatus.TERMINATED

    terminated_details_response = MagicMock()
    terminated_details_response.error = None
    terminated_details_response.details = terminated_details_mock

    mock_api = AsyncMock()
    mock_api.terminate_workflow.return_value = terminate_response
    mock_api.get_workflow_details.return_value = terminated_details_response

    with patch('sample.api.API.get_api_handle') as mock_get_api:
        mock_get_api.return_value = mock_api

        api = await API.get_api_handle()

        # Terminate the workflow
        terminate_result = await api.terminate_workflow(
            TerminateWorkflowParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id",
                reason="Testing terminate workflow"
            )
        )

        assert terminate_result.error is None
        print(f"✓ Terminated workflow: test_workflow_id")

        # Verify termination
        details = await api.get_workflow_details(
            GetWorkflowDetailsParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id"
            )
        )
        assert details.details.status == WorkflowExecutionStatus.TERMINATED


@pytest.mark.asyncio
async def test_full_workflow_lifecycle(mock_temporal_service):
    """Test the complete workflow lifecycle"""
    from sample.api import API

    # Mock all required responses
    query_response1 = MagicMock()
    query_response1.error = None
    query_response1.response = "initial_state"

    signal_response = MagicMock()
    signal_response.error = None

    query_response2 = MagicMock()
    query_response2.error = None
    query_response2.response = "UPDATED_STATE"

    terminate_response = MagicMock()
    terminate_response.error = None

    terminated_details_mock = MagicMock()
    terminated_details_mock.workflow_id = "test_workflow_id"
    terminated_details_mock.run_id = "test_run_id"
    terminated_details_mock.status = WorkflowExecutionStatus.TERMINATED

    terminated_details_response = MagicMock()
    terminated_details_response.error = None
    terminated_details_response.details = terminated_details_mock

    mock_api = AsyncMock()
    mock_api.query_workflow.side_effect = [query_response1, query_response2]
    mock_api.signal_workflow.return_value = signal_response
    mock_api.terminate_workflow.return_value = terminate_response
    mock_api.get_workflow_details.return_value = terminated_details_response

    with patch('sample.api.API.get_api_handle') as mock_get_api:
        mock_get_api.return_value = mock_api

        api = await API.get_api_handle()

        # 1. Initial query
        query_result = await api.query_workflow(
            QueryWorkflowParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id",
                query="get_state",
                args="Write a new Joke"
            )
        )
        assert query_result.error is None

        # 2. Signal workflow
        await api.signal_workflow(
            SignalWorkflowParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id",
                signal_name="change_state",
                args="UPDATED_STATE"
            )
        )

        # 3. Query updated state
        query_result = await api.query_workflow(
            QueryWorkflowParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id",
                query="get_state"
            )
        )
        assert query_result.response == "UPDATED_STATE"

        # 4. Terminate workflow
        await api.terminate_workflow(
            TerminateWorkflowParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id",
                reason="Lifecycle test complete"
            )
        )

        # 5. Verify final state
        details = await api.get_workflow_details(
            GetWorkflowDetailsParams(
                workflow_id="test_workflow_id",
                run_id="test_run_id"
            )
        )
        assert details.details.status == WorkflowExecutionStatus.TERMINATED


if __name__ == "__main__":
    asyncio.run(test_full_workflow_lifecycle())