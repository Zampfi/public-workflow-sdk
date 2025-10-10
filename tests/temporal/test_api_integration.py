from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sample.api import API, run_workflow, execute_workflow, list_workflows
from zamp_public_workflow_sdk.temporal.models.temporal_models import (
    CancelWorkflowParams,
    GetWorkflowDetailsParams,
    QueryWorkflowParams,
    SignalWorkflowParams,
    TerminateWorkflowParams,
    WorkflowExecutionStatus,
)


@pytest.mark.asyncio
async def test_create_workflow(temporal_service):
    """Test workflow creation"""

    # Mock the API response
    mock_result = MagicMock()
    mock_result.error = None
    mock_result.run_id = "test_run_id"

    # Patch TemporalService.connect to return our mock service
    with patch("sample.api.TemporalService.connect", return_value=temporal_service):
        # Mock the start_async_workflow method
        temporal_service.start_async_workflow = AsyncMock(return_value=mock_result)

        workflow_id, run_id, result = await run_workflow()

        assert result.error is None
        assert workflow_id is not None  # Generated UUID
        assert run_id == "test_run_id"
        print(f"✓ Created workflow: {workflow_id} with run_id: {run_id}")
        return workflow_id, run_id


@pytest.mark.asyncio
async def test_list_workflows(temporal_service):
    """Test workflow listing"""

    # Create mock workflow objects
    mock_workflow = MagicMock()
    mock_workflow.workflow_id = "test_workflow_id"
    mock_workflow.run_id = "test_run_id"
    mock_workflow.workflow_type = "JokeWorkflow"

    # Patch TemporalService.connect to return our mock service
    with patch("sample.api.TemporalService.connect", return_value=temporal_service):
        # Mock the list_workflows method
        temporal_service.list_workflows = AsyncMock(return_value=[mock_workflow])

        workflows = await list_workflows()

        assert len(workflows) > 0
        workflow = workflows[0]
        assert workflow.workflow_type == "JokeWorkflow"
        assert workflow.run_id == mock_workflow.run_id
        print(f"✓ Listed workflows, found target workflow: {mock_workflow.workflow_id}")


@pytest.mark.asyncio
async def test_get_workflow_details(temporal_service):
    """Test getting workflow details for a specific workflow"""
    with patch("sample.api.TemporalService.connect", return_value=temporal_service):
        # First create a workflow
        workflow_id, run_id = await test_create_workflow(temporal_service)
        await asyncio.sleep(2)

        # Mock get_workflow_details
        mock_details = MagicMock()
        mock_details.error = None
        mock_details_data = MagicMock()
        mock_details_data.workflow_id = workflow_id
        mock_details_data.run_id = run_id
        mock_details.details = mock_details_data
        temporal_service.get_workflow_details = AsyncMock(return_value=mock_details)

        # Get API handle and get details directly
        api = await API.get_api_handle()
        details = await api.get_workflow_details(GetWorkflowDetailsParams(workflow_id=workflow_id, run_id=run_id))

        assert details.error is None
        assert details.details is not None
        assert details.details.workflow_id == workflow_id
        assert details.details.run_id == run_id
        print(f"✓ Got details for workflow: {workflow_id}")


@pytest.mark.asyncio
async def test_query_workflow(temporal_service):
    """Test querying a specific workflow"""
    with patch("sample.api.TemporalService.connect", return_value=temporal_service):
        # First create a workflow
        workflow_id, run_id = await test_create_workflow(temporal_service)
        await asyncio.sleep(2)

        # Mock query_workflow
        mock_query_result = MagicMock()
        mock_query_result.error = None
        mock_query_result.response = "mock_state"
        temporal_service.query_workflow = AsyncMock(return_value=mock_query_result)

        # Query the specific workflow
        api = await API.get_api_handle()
        query_result = await api.query_workflow(
            QueryWorkflowParams(
                workflow_id=workflow_id,
                run_id=run_id,
                query="get_state",
                args="Write a new Joke",
            )
        )

        assert query_result.error is None
        assert query_result.response is not None
        print(f"✓ Queried workflow {workflow_id}, state: {query_result.response}")


@pytest.mark.asyncio
async def test_signal_workflow(temporal_service):
    """Test signaling a specific workflow"""
    with patch("sample.api.TemporalService.connect", return_value=temporal_service):
        # First create a workflow
        workflow_id, run_id = await test_create_workflow(temporal_service)
        await asyncio.sleep(2)

        # Mock signal_workflow
        mock_signal_result = MagicMock()
        mock_signal_result.error = None
        temporal_service.signal_workflow = AsyncMock(return_value=mock_signal_result)

        # Mock query_workflow
        mock_query_result = MagicMock()
        mock_query_result.error = None
        mock_query_result.response = "Write a new Joke"
        temporal_service.query_workflow = AsyncMock(return_value=mock_query_result)

        # Signal the specific workflow
        api = await API.get_api_handle()
        signal_result = await api.signal_workflow(
            SignalWorkflowParams(
                workflow_id=workflow_id,
                run_id=run_id,
                signal_name="change_state",
                args="Write a new Joke",
            )
        )

        assert signal_result.error is None
        print("✓ Signaled workflow: test_workflow_id")

        # Verify state change through query
        query_result = await api.query_workflow(
            QueryWorkflowParams(workflow_id=workflow_id, run_id=run_id, query="get_state")
        )
        assert query_result.response == "Write a new Joke"


@pytest.mark.asyncio
async def test_execute_sync_workflow(temporal_service):
    """Test executing a synchronous workflow"""

    mock_result = MagicMock()
    mock_result.error = None
    mock_result.result = "Test execution result"

    # Patch TemporalService.connect to return our mock service
    with patch("sample.api.TemporalService.connect", return_value=temporal_service):
        # Mock the start_sync_workflow method
        temporal_service.start_sync_workflow = AsyncMock(return_value=mock_result)

        result = await execute_workflow()

        assert result.error is None
        assert result.result is not None
        print(f"✓ Executed sync workflow with result: {result.result}")


@pytest.mark.asyncio
async def test_cancel_workflow(temporal_service):
    """Test canceling a specific workflow"""
    with patch("sample.api.TemporalService.connect", return_value=temporal_service):
        # First create a workflow
        workflow_id, run_id = await test_create_workflow(temporal_service)
        await asyncio.sleep(2)

        # Mock cancel_workflow
        mock_cancel_result = MagicMock()
        mock_cancel_result.error = None
        temporal_service.cancel_workflow = AsyncMock(return_value=mock_cancel_result)

        # Mock get_workflow_details
        mock_details = MagicMock()
        mock_details.error = None
        mock_details_data = MagicMock()
        mock_details_data.workflow_id = workflow_id
        mock_details_data.run_id = run_id
        mock_details_data.status = WorkflowExecutionStatus.CANCELED
        mock_details.details = mock_details_data
        temporal_service.get_workflow_details = AsyncMock(return_value=mock_details)

        # Cancel the specific workflow
        api = await API.get_api_handle()
        cancel_result = await api.cancel_workflow(CancelWorkflowParams(workflow_id=workflow_id, run_id=run_id))

        assert cancel_result.error is None
        print("✓ Canceled workflow: test_workflow_id")

        # Verify cancellation
        await asyncio.sleep(2)
        details = await api.get_workflow_details(GetWorkflowDetailsParams(workflow_id=workflow_id, run_id=run_id))
        assert details.details.status == WorkflowExecutionStatus.CANCELED


@pytest.mark.asyncio
async def test_terminate_workflow(temporal_service):
    """Test terminating a specific workflow"""
    with patch("sample.api.TemporalService.connect", return_value=temporal_service):
        # First create a workflow
        workflow_id, run_id = await test_create_workflow(temporal_service)
        await asyncio.sleep(2)

        # Mock terminate_workflow
        mock_terminate_result = MagicMock()
        mock_terminate_result.error = None
        temporal_service.terminate_workflow = AsyncMock(return_value=mock_terminate_result)

        # Mock get_workflow_details
        mock_details = MagicMock()
        mock_details.error = None
        mock_details_data = MagicMock()
        mock_details_data.workflow_id = workflow_id
        mock_details_data.run_id = run_id
        mock_details_data.status = WorkflowExecutionStatus.TERMINATED
        mock_details.details = mock_details_data
        temporal_service.get_workflow_details = AsyncMock(return_value=mock_details)

        # Terminate the specific workflow
        api = await API.get_api_handle()
        terminate_result = await api.terminate_workflow(
            TerminateWorkflowParams(workflow_id=workflow_id, run_id=run_id, reason="Testing terminate workflow")
        )

        assert terminate_result.error is None
        print("✓ Terminated workflow: test_workflow_id")

        # Verify termination
        await asyncio.sleep(2)
        details = await api.get_workflow_details(GetWorkflowDetailsParams(workflow_id=workflow_id, run_id=run_id))
        assert details.details.status == WorkflowExecutionStatus.TERMINATED


@pytest.mark.asyncio
async def test_full_workflow_lifecycle(temporal_service):
    """Test the complete workflow lifecycle"""
    from sample.api import API

    # Define workflow_id and run_id for this test
    workflow_id = "test_workflow_id"
    run_id = "test_run_id"

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
    terminated_details_mock.workflow_id = workflow_id
    terminated_details_mock.run_id = run_id
    terminated_details_mock.status = WorkflowExecutionStatus.TERMINATED

    terminated_details_response = MagicMock()
    terminated_details_response.error = None
    terminated_details_response.details = terminated_details_mock

    mock_api = AsyncMock()
    mock_api.query_workflow.side_effect = [query_response1, query_response2]
    mock_api.signal_workflow.return_value = signal_response
    mock_api.terminate_workflow.return_value = terminate_response
    mock_api.get_workflow_details.return_value = terminated_details_response

    with patch("sample.api.API.get_api_handle") as mock_get_api:
        mock_get_api.return_value = mock_api

        api = await API.get_api_handle()

    query_result = await api.query_workflow(
        QueryWorkflowParams(
            workflow_id=workflow_id,
            run_id=run_id,
            query="get_state",
            args="Write a new Joke",
        )
    )

    assert query_result.error is None

    await api.signal_workflow(
        SignalWorkflowParams(
            workflow_id=workflow_id,
            run_id=run_id,
            signal_name="change_state",
            args="UPDATED_STATE",
        )
    )

    # 4. Query updated state
    query_result = await api.query_workflow(
        QueryWorkflowParams(workflow_id=workflow_id, run_id=run_id, query="get_state")
    )
    await asyncio.sleep(2)
    assert query_result.response == "UPDATED_STATE"

    # 5. Terminate workflow
    await api.terminate_workflow(
        TerminateWorkflowParams(workflow_id=workflow_id, run_id=run_id, reason="Lifecycle test complete")
    )

    # 6. Verify final state
    await asyncio.sleep(2)
    details = await api.get_workflow_details(GetWorkflowDetailsParams(workflow_id=workflow_id, run_id=run_id))
    assert details.details.status == WorkflowExecutionStatus.TERMINATED


if __name__ == "__main__":
    asyncio.run(test_full_workflow_lifecycle())
