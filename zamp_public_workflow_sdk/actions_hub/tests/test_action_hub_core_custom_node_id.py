"""
Unit tests for ActionsHub custom node_id handling in execute_activity.

This module tests the custom_node_id parameter functionality in execute_activity.
"""

from unittest.mock import Mock, patch

import pytest

from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode
from zamp_public_workflow_sdk.simulation.models import ExecutionType
from zamp_public_workflow_sdk.temporal.interceptors.node_id_interceptor import TEMPORAL_NODE_ID_KEY


class TestActionsHubCustomNodeId:
    """Test cases for ActionsHub custom node_id parameter handling."""

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
    async def test_execute_activity_with_custom_node_id_parameter(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity when custom_node_id is provided via parameter."""
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

        # Execute activity with custom_node_id parameter
        await ActionsHub.execute_activity("test_activity", "arg1_value", custom_node_id="custom_node_id#123")

        # Verify execute_activity was called
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

        assert len(call_args[1]["args"]) > 0
        first_arg = call_args[1]["args"][0]
        assert isinstance(first_arg, dict)
        assert TEMPORAL_NODE_ID_KEY in first_arg
        assert first_arg[TEMPORAL_NODE_ID_KEY] == "custom_node_id#123"

        # Verify that "arg1_value" is still in the args (as second argument)
        assert len(call_args[1]["args"]) >= 2
        assert call_args[1]["args"][1] == "arg1_value"

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_activity")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._generate_node_id_for_action")
    async def test_execute_activity_without_custom_node_id_parameter(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity when custom_node_id parameter is NOT provided."""
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

        # Execute activity without custom_node_id parameter (defaults to None)
        await ActionsHub.execute_activity("test_activity", "arg1_value")

        # Verify execute_activity was called
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

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
    async def test_execute_activity_with_args_that_are_dicts(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity when arguments include regular dicts (not treated as custom node_id)."""
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

        # Execute activity with a dict argument (not treated as custom node_id)
        regular_dict = {"some_key": "some_value"}
        await ActionsHub.execute_activity("test_activity", "arg1_value", regular_dict)

        # Verify execute_activity was called
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

        assert len(call_args[1]["args"]) > 0
        first_arg = call_args[1]["args"][0]
        assert isinstance(first_arg, dict)
        assert TEMPORAL_NODE_ID_KEY in first_arg
        assert first_arg[TEMPORAL_NODE_ID_KEY] == "test_activity#1"  # Generated node_id

        # Verify that regular arguments are preserved
        assert len(call_args[1]["args"]) >= 3
        assert call_args[1]["args"][1] == "arg1_value"
        assert call_args[1]["args"][2] == regular_dict

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_activity")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._generate_node_id_for_action")
    async def test_execute_activity_with_no_args(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity with no positional args."""
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
    async def test_execute_activity_with_multiple_args_and_custom_node_id_parameter(
        self,
        mock_generate_node_id,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_activity,
    ):
        """Test execute_activity with multiple args and custom_node_id parameter."""
        # Setup mocks
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_generate_node_id.return_value = ("test_activity", "test-workflow", "test_activity#1")
        mock_get_simulation_response.return_value = Mock(execution_type=ExecutionType.EXECUTE, execution_response=None)
        mock_execute_activity.return_value = "activity_result"

        # Register a test activity
        @ActionsHub.register_activity("Test activity")
        async def test_activity(arg1: str, arg2: int, arg3: list) -> str:
            return "test_result"

        # Execute activity with multiple args and custom_node_id parameter
        await ActionsHub.execute_activity(
            "test_activity", "arg1_value", 42, ["item1", "item2"], custom_node_id="custom_node_id#999"
        )

        # Verify execute_activity was called
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

        assert len(call_args[1]["args"]) > 0
        first_arg = call_args[1]["args"][0]
        assert isinstance(first_arg, dict)
        assert TEMPORAL_NODE_ID_KEY in first_arg
        assert first_arg[TEMPORAL_NODE_ID_KEY] == "custom_node_id#999"  # Custom node_id

        # Verify all other args are still present
        assert len(call_args[1]["args"]) >= 4
        assert call_args[1]["args"][1] == "arg1_value"
        assert call_args[1]["args"][2] == 42
        assert call_args[1]["args"][3] == ["item1", "item2"]
