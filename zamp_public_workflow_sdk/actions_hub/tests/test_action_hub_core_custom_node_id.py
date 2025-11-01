"""
Unit tests for ActionsHub custom node_id handling in execute_activity.

This module tests the functionality that checks if a caller provided
a custom node_id in the last argument (lines 525-526 in action_hub_core.py).
"""

from unittest.mock import Mock, patch

import pytest

from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode
from zamp_public_workflow_sdk.simulation.models import ExecutionType
from zamp_public_workflow_sdk.temporal.interceptors.node_id_interceptor import TEMPORAL_NODE_ID_KEY


class TestActionsHubCustomNodeId:
    """Test cases for ActionsHub custom node_id handling."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear the node ID tracker before each test
        ActionsHub.clear_node_id_tracker()
        # Clear activities to avoid conflicts
        ActionsHub._activities.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        # Clear the node ID tracker after each test
        ActionsHub.clear_node_id_tracker()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_activity")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._generate_node_id_for_action")
    async def test_execute_activity_with_custom_node_id_in_last_arg(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity when custom node_id is provided in last argument."""
        # Setup mocks
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_generate_node_id.return_value = ("test_activity", "test-workflow", "test_activity#1")
        mock_get_simulation_response.return_value = Mock(execution_type=ExecutionType.EXECUTE, execution_response=None)
        mock_execute_activity.return_value = "activity_result"

        # Register a test activity
        @ActionsHub.register_activity("Test activity")
        async def test_activity(arg1: str, custom_node_id: dict) -> str:
            return "test_result"

        # Execute activity with custom node_id in last argument
        custom_node_id_dict = {TEMPORAL_NODE_ID_KEY: "custom_node_id#123"}
        await ActionsHub.execute_activity("test_activity", "arg1_value", custom_node_id_dict)

        # Verify execute_activity was called
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

        # Check that the custom node_id was used and the last arg was removed from args
        # The custom_node_id_dict should be prepended to args
        assert len(call_args[1]["args"]) > 0
        first_arg = call_args[1]["args"][0]
        assert isinstance(first_arg, dict)
        assert TEMPORAL_NODE_ID_KEY in first_arg
        assert first_arg[TEMPORAL_NODE_ID_KEY] == "custom_node_id#123"

        # Verify that "arg1_value" is still in the args (as second argument)
        assert len(call_args[1]["args"]) >= 2
        assert call_args[1]["args"][1] == "arg1_value"

        # Verify custom_node_id_dict was removed from the end
        # (it should only appear once as the first arg)
        node_id_args = [arg for arg in call_args[1]["args"] if isinstance(arg, dict) and TEMPORAL_NODE_ID_KEY in arg]
        assert len(node_id_args) == 1  # Should only be one node_id dict

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_activity")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._generate_node_id_for_action")
    async def test_execute_activity_without_custom_node_id_in_last_arg(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity when custom node_id is NOT provided in last argument."""
        # Setup mocks
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_generate_node_id.return_value = ("test_activity", "test-workflow", "test_activity#1")
        mock_get_simulation_response.return_value = Mock(execution_type=ExecutionType.EXECUTE, execution_response=None)
        mock_execute_activity.return_value = "activity_result"

        # Register a test activity
        @ActionsHub.register_activity("Test activity")
        async def test_activity(arg1: str) -> str:
            return "test_result"

        # Execute activity without custom node_id in last argument
        await ActionsHub.execute_activity("test_activity", "arg1_value")

        # Verify execute_activity was called
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

        # Check that the generated node_id was used (not a custom one)
        assert len(call_args[1]["args"]) > 0
        first_arg = call_args[1]["args"][0]
        assert isinstance(first_arg, dict)
        assert TEMPORAL_NODE_ID_KEY in first_arg
        assert first_arg[TEMPORAL_NODE_ID_KEY] == "test_activity#1"  # Generated node_id

        # Verify that "arg1_value" is still in the args
        assert len(call_args[1]["args"]) >= 2
        assert call_args[1]["args"][1] == "arg1_value"

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_activity")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._generate_node_id_for_action")
    async def test_execute_activity_with_dict_not_containing_node_id_key(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity when last argument is a dict but doesn't contain TEMPORAL_NODE_ID_KEY."""
        # Setup mocks
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_generate_node_id.return_value = ("test_activity", "test-workflow", "test_activity#1")
        mock_get_simulation_response.return_value = Mock(execution_type=ExecutionType.EXECUTE, execution_response=None)
        mock_execute_activity.return_value = "activity_result"

        # Register a test activity
        @ActionsHub.register_activity("Test activity")
        async def test_activity(arg1: str, some_dict: dict) -> str:
            return "test_result"

        # Execute activity with a dict in last position that doesn't have TEMPORAL_NODE_ID_KEY
        regular_dict = {"some_key": "some_value"}
        await ActionsHub.execute_activity("test_activity", "arg1_value", regular_dict)

        # Verify execute_activity was called
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

        # Check that the generated node_id was used (not treated as custom)
        assert len(call_args[1]["args"]) > 0
        first_arg = call_args[1]["args"][0]
        assert isinstance(first_arg, dict)
        assert TEMPORAL_NODE_ID_KEY in first_arg
        assert first_arg[TEMPORAL_NODE_ID_KEY] == "test_activity#1"  # Generated node_id

        # Verify that regular_dict was NOT removed and is still in args
        assert len(call_args[1]["args"]) >= 3
        assert call_args[1]["args"][1] == "arg1_value"
        assert call_args[1]["args"][2] == regular_dict

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_activity")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._generate_node_id_for_action")
    async def test_execute_activity_with_empty_args(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity with no args (empty args list)."""
        # Setup mocks
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_generate_node_id.return_value = ("test_activity", "test-workflow", "test_activity#1")
        mock_get_simulation_response.return_value = Mock(execution_type=ExecutionType.EXECUTE, execution_response=None)
        mock_execute_activity.return_value = "activity_result"

        # Register a test activity with no arguments
        @ActionsHub.register_activity("Test activity")
        async def test_activity() -> str:
            return "test_result"

        # Execute activity with no args
        await ActionsHub.execute_activity("test_activity")

        # Verify execute_activity was called
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

        # Check that only the generated node_id is in args
        assert len(call_args[1]["args"]) == 1
        first_arg = call_args[1]["args"][0]
        assert isinstance(first_arg, dict)
        assert TEMPORAL_NODE_ID_KEY in first_arg
        assert first_arg[TEMPORAL_NODE_ID_KEY] == "test_activity#1"  # Generated node_id

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_activity")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._generate_node_id_for_action")
    async def test_execute_activity_with_multiple_args_and_custom_node_id(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity with multiple args and custom node_id in last position."""
        # Setup mocks
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_generate_node_id.return_value = ("test_activity", "test-workflow", "test_activity#1")
        mock_get_simulation_response.return_value = Mock(execution_type=ExecutionType.EXECUTE, execution_response=None)
        mock_execute_activity.return_value = "activity_result"

        # Register a test activity
        @ActionsHub.register_activity("Test activity")
        async def test_activity(arg1: str, arg2: int, arg3: list, custom_node_id: dict) -> str:
            return "test_result"

        # Execute activity with multiple args and custom node_id in last position
        custom_node_id_dict = {TEMPORAL_NODE_ID_KEY: "custom_node_id#999"}
        await ActionsHub.execute_activity("test_activity", "arg1_value", 42, ["item1", "item2"], custom_node_id_dict)

        # Verify execute_activity was called
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

        # Check that custom node_id was used and prepended
        assert len(call_args[1]["args"]) > 0
        first_arg = call_args[1]["args"][0]
        assert isinstance(first_arg, dict)
        assert TEMPORAL_NODE_ID_KEY in first_arg
        assert first_arg[TEMPORAL_NODE_ID_KEY] == "custom_node_id#999"

        # Verify all other args are still present (except the last one which was the custom_node_id_dict)
        assert len(call_args[1]["args"]) >= 4
        assert call_args[1]["args"][1] == "arg1_value"
        assert call_args[1]["args"][2] == 42
        assert call_args[1]["args"][3] == ["item1", "item2"]

        # Verify custom_node_id_dict was removed from the end
        assert len([arg for arg in call_args[1]["args"] if isinstance(arg, dict) and TEMPORAL_NODE_ID_KEY in arg]) == 1
