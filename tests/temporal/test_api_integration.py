from __future__ import annotations

import asyncio

import pytest

from sample.api import API, create_workflow, execute_workflow, list_workflows
from zamp_public_workflow_sdk.temporal.models.temporal_models import (
    CancelWorkflowParams,
    GetWorkflowDetailsParams,
    QueryWorkflowParams,
    SignalWorkflowParams,
    TerminateWorkflowParams,
    WorkflowExecutionStatus,
)


@pytest.mark.asyncio
async def test_create_workflow():
    """Test workflow creation"""
    workflow_id, run_id, result = await create_workflow()

    assert result.error is None
    assert workflow_id is not None
    assert run_id is not None
    print(f"✓ Created workflow: {workflow_id} with run_id: {run_id}")
    return workflow_id, run_id


@pytest.mark.asyncio
async def test_list_workflows():
    """Test workflow listing after creating one"""
    # First create a workflow
    workflow_id, run_id = await test_create_workflow()
    await asyncio.sleep(2)  # Wait for workflow to be visible

    # List workflows
    workflows = await list_workflows()

    assert len(workflows) > 0
    workflow = next(w for w in workflows if w.workflow_id == workflow_id)
    assert workflow.workflow_type == "JokeWorkflow"
    assert workflow.run_id == run_id
    print(f"✓ Listed workflows, found target workflow: {workflow_id}")


@pytest.mark.asyncio
async def test_get_workflow_details():
    """Test getting workflow details for a specific workflow"""
    # First create a workflow
    workflow_id, run_id = await test_create_workflow()
    await asyncio.sleep(2)

    # Get API handle and get details directly
    api = await API.get_api_handle()
    details = await api.get_workflow_details(GetWorkflowDetailsParams(workflow_id=workflow_id, run_id=run_id))

    assert details.error is None
    assert details.details is not None
    assert details.details.workflow_id == workflow_id
    assert details.details.run_id == run_id
    print(f"✓ Got details for workflow: {workflow_id}")


@pytest.mark.asyncio
async def test_query_workflow():
    """Test querying a specific workflow"""
    # First create a workflow
    workflow_id, run_id = await test_create_workflow()
    await asyncio.sleep(2)

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
async def test_signal_workflow():
    """Test signaling a specific workflow"""
    # First create a workflow
    workflow_id, run_id = await test_create_workflow()
    await asyncio.sleep(2)

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
    print(f"✓ Signaled workflow: {workflow_id}")

    # Verify state change through query
    query_result = await api.query_workflow(
        QueryWorkflowParams(workflow_id=workflow_id, run_id=run_id, query="get_state")
    )
    assert query_result.response == "Write a new Joke"


@pytest.mark.asyncio
async def test_execute_sync_workflow():
    """Test executing a synchronous workflow"""
    result = await execute_workflow()

    assert result.error is None
    assert result.result is not None
    print(f"✓ Executed sync workflow with result: {result.result}")


@pytest.mark.asyncio
async def test_cancel_workflow():
    """Test canceling a specific workflow"""
    # First create a workflow
    workflow_id, run_id = await test_create_workflow()
    await asyncio.sleep(2)

    # Cancel the specific workflow
    api = await API.get_api_handle()
    cancel_result = await api.cancel_workflow(CancelWorkflowParams(workflow_id=workflow_id, run_id=run_id))

    assert cancel_result.error is None
    print(f"✓ Canceled workflow: {workflow_id}")

    # Verify cancellation
    await asyncio.sleep(2)
    details = await api.get_workflow_details(GetWorkflowDetailsParams(workflow_id=workflow_id, run_id=run_id))
    assert details.details.status == WorkflowExecutionStatus.CANCELED


@pytest.mark.asyncio
async def test_terminate_workflow():
    """Test terminating a specific workflow"""
    # First create a workflow
    workflow_id, run_id = await test_create_workflow()
    await asyncio.sleep(2)

    # Terminate the specific workflow
    api = await API.get_api_handle()
    terminate_result = await api.terminate_workflow(
        TerminateWorkflowParams(workflow_id=workflow_id, run_id=run_id, reason="Testing terminate workflow")
    )

    assert terminate_result.error is None
    print(f"✓ Terminated workflow: {workflow_id}")

    # Verify termination
    await asyncio.sleep(2)
    details = await api.get_workflow_details(GetWorkflowDetailsParams(workflow_id=workflow_id, run_id=run_id))
    assert details.details.status == WorkflowExecutionStatus.TERMINATED


@pytest.mark.asyncio
async def test_full_workflow_lifecycle():
    """Test the complete workflow lifecycle"""
    # 1. Create workflow
    workflow_id, run_id = await test_create_workflow()
    await asyncio.sleep(2)

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
