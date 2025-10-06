from types import SimpleNamespace

import pytest

from zamp_public_workflow_sdk.actions_hub.action_hub_core import (
    ActionsHub,
    NODE_ID_HEADER_KEY,
    TEMPORAL_NODE_ID_KEY,
    workflow,
)
from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode


@pytest.fixture(autouse=True)
def reset_actions_hub_state():
    """Ensure each test starts with a clean tracker state."""
    ActionsHub.clear_node_id_tracker()
    ActionsHub._activities.clear()
    ActionsHub._workflows.clear()
    yield
    ActionsHub.clear_node_id_tracker()
    ActionsHub._activities.clear()
    ActionsHub._workflows.clear()


def test_node_id_hierarchy_with_context_stack(monkeypatch):
    workflow_id = "wf-test"

    monkeypatch.setattr(
        ActionsHub,
        "_get_current_workflow_id",
        classmethod(lambda cls: workflow_id),
    )
    monkeypatch.setattr(
        workflow,
        "info",
        lambda: SimpleNamespace(headers=None),
    )

    # First level child workflow context
    ActionsHub._push_node_id_context(workflow_id, "ChildWorkflow#1")
    node_id_first = ActionsHub._get_node_id(workflow_id, "Activity")
    assert node_id_first == "ChildWorkflow#1.Activity#1"

    # Nested child workflow context
    ActionsHub._push_node_id_context(workflow_id, "NestedChild#1")
    node_id_nested = ActionsHub._get_node_id(workflow_id, "Activity")
    assert node_id_nested == "ChildWorkflow#1.NestedChild#1.Activity#1"

    # Subsequent call in same nested context increments counter
    node_id_nested_second = ActionsHub._get_node_id(workflow_id, "Activity")
    assert node_id_nested_second == "ChildWorkflow#1.NestedChild#1.Activity#2"

    # Pop back to first level context
    ActionsHub._pop_node_id_context(workflow_id)
    node_id_after_pop = ActionsHub._get_node_id(workflow_id, "Activity")
    assert node_id_after_pop == "ChildWorkflow#1.Activity#2"

    # Clear context entirely
    ActionsHub._pop_node_id_context(workflow_id)
    node_id_root = ActionsHub._get_node_id(workflow_id, "Activity")
    assert node_id_root == "Activity#1"


def test_get_node_id_uses_header_when_context_missing(monkeypatch):
    workflow_id = "wf-header"

    monkeypatch.setattr(
        ActionsHub,
        "_get_current_workflow_id",
        classmethod(lambda cls: workflow_id),
    )

    class DummyConverter:
        def from_payload(self, payload, typ):
            assert payload == "parent-context"
            assert typ is str
            return "ParentWorkflow#3"

    monkeypatch.setattr(
        workflow,
        "info",
        lambda: SimpleNamespace(headers={NODE_ID_HEADER_KEY: "parent-context"}),
    )
    monkeypatch.setattr(workflow, "payload_converter", lambda: DummyConverter())

    node_id = ActionsHub._get_node_id(workflow_id, "ChildActivity")
    assert node_id == "ParentWorkflow#3.ChildActivity#1"


@pytest.mark.asyncio
async def test_execute_child_workflow_temporal_mode(monkeypatch):
    workflow_id = "wf-temporal"
    monkeypatch.setattr(
        ActionsHub,
        "_get_current_workflow_id",
        classmethod(lambda cls: workflow_id),
    )
    monkeypatch.setattr(
        "zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context",
        lambda: ExecutionMode.TEMPORAL,
    )
    monkeypatch.setattr(workflow, "info", lambda: SimpleNamespace(headers=None))
    monkeypatch.setattr(workflow, "payload_converter", lambda: None)

    captured = {}

    async def fake_execute_child_workflow(workflow_name, args=(), result_type=None, **kwargs):
        captured["workflow_name"] = workflow_name
        captured["args"] = args
        captured["result_type"] = result_type
        captured["context_snapshot"] = ActionsHub._parent_node_id_tracker.get(workflow_id)
        return "child-result"

    monkeypatch.setattr(workflow, "execute_child_workflow", fake_execute_child_workflow)

    result = await ActionsHub.execute_child_workflow("child_workflow", 1, 2, result_type=dict)

    assert result == "child-result"
    assert captured["workflow_name"] == "child_workflow"
    assert captured["result_type"] is dict
    node_id_arg, *activity_args = captured["args"]
    assert node_id_arg == {TEMPORAL_NODE_ID_KEY: "child_workflow#1"}
    assert activity_args == [1, 2]
    assert captured["context_snapshot"] == ["child_workflow#1"]
    assert ActionsHub._parent_node_id_tracker.get(workflow_id) is None


@pytest.mark.asyncio
async def test_execute_child_workflow_api_mode(monkeypatch):
    workflow_id = "wf-api"
    monkeypatch.setattr(
        ActionsHub,
        "_get_current_workflow_id",
        classmethod(lambda cls: workflow_id),
    )
    monkeypatch.setattr(
        "zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context",
        lambda: ExecutionMode.API,
    )
    monkeypatch.setattr(workflow, "info", lambda: SimpleNamespace(headers=None))

    async def child_callable(*args):
        assert ActionsHub._parent_node_id_tracker[workflow_id] == ["child_callable#1"]
        return "api-result"

    result = await ActionsHub.execute_child_workflow(child_callable, "arg1")

    assert result == "api-result"
    assert ActionsHub._parent_node_id_tracker.get(workflow_id) is None


@pytest.mark.asyncio
async def test_execute_activity_forwards_result_type(monkeypatch):
    workflow_id = "wf-activity"
    monkeypatch.setattr(
        ActionsHub,
        "_get_current_workflow_id",
        classmethod(lambda cls: workflow_id),
    )
    monkeypatch.setattr(
        "zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context",
        lambda: ExecutionMode.TEMPORAL,
    )
    monkeypatch.setattr(workflow, "info", lambda: SimpleNamespace(headers=None))

    captured = {}

    async def fake_execute_activity(activity_name, args=(), result_type=None, **kwargs):
        captured["activity_name"] = activity_name
        captured["args"] = args
        captured["result_type"] = result_type
        return "activity-result"

    monkeypatch.setattr(workflow, "execute_activity", fake_execute_activity)

    result = await ActionsHub.execute_activity("test_activity", str, "arg1", "arg2")

    assert result == "activity-result"
    assert captured["activity_name"] == "test_activity"
    node_id_arg, *activity_args = captured["args"]
    assert node_id_arg == {TEMPORAL_NODE_ID_KEY: "test_activity#1"}
    assert activity_args == ["arg1", "arg2"]
    assert captured["result_type"] is str


@pytest.mark.asyncio
async def test_start_child_workflow_forwards_result_type(monkeypatch):
    workflow_id = "wf-start"
    monkeypatch.setattr(
        ActionsHub,
        "_get_current_workflow_id",
        classmethod(lambda cls: workflow_id),
    )
    monkeypatch.setattr(workflow, "info", lambda: SimpleNamespace(headers=None))

    captured = {}

    async def fake_start_child_workflow(workflow_name, args=(), result_type=None, **kwargs):
        captured["workflow_name"] = workflow_name
        captured["args"] = args
        captured["result_type"] = result_type
        return "handle"

    monkeypatch.setattr(workflow, "start_child_workflow", fake_start_child_workflow)

    result = await ActionsHub.start_child_workflow("child_workflow", "payload", result_type=list)

    assert result == "handle"
    assert captured["workflow_name"] == "child_workflow"
    node_id_arg, *child_args = captured["args"]
    assert node_id_arg == {TEMPORAL_NODE_ID_KEY: "child_workflow#1"}
    assert child_args == ["payload"]
    assert captured["result_type"] is list
