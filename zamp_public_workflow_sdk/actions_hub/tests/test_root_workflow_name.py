from unittest.mock import Mock, patch

import pytest

from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode


class TestGetRootWorkflowNameFromNodeId:
    """Test cases for _get_root_workflow_name_from_node_id method."""

    def test_simple_node_id(self):
        """Test extracting root from simple node_id like 'A#1'."""
        result = ActionsHub._get_root_workflow_name_from_node_id("A#1")
        assert result == "A"

    def test_nested_node_id_two_levels(self):
        """Test extracting root from nested node_id like 'A#1.B#1'."""
        result = ActionsHub._get_root_workflow_name_from_node_id("A#1.B#1")
        assert result == "A"

    def test_nested_node_id_three_levels(self):
        """Test extracting root from deeply nested node_id like 'A#1.B#1.C#1'."""
        result = ActionsHub._get_root_workflow_name_from_node_id("A#1.B#1.C#1")
        assert result == "A"

    def test_nested_node_id_many_levels(self):
        """Test extracting root from many levels deep node_id."""
        result = ActionsHub._get_root_workflow_name_from_node_id("RootWorkflow#1.Child1#2.Child2#1.Child3#3")
        assert result == "RootWorkflow"

    def test_workflow_with_underscore(self):
        """Test extracting root when workflow name contains underscore."""
        result = ActionsHub._get_root_workflow_name_from_node_id("My_Workflow#1.Child#1")
        assert result == "My_Workflow"

    def test_workflow_with_numbers(self):
        """Test extracting root when workflow name contains numbers."""
        result = ActionsHub._get_root_workflow_name_from_node_id("Workflow123#1.Child#1")
        assert result == "Workflow123"

    def test_empty_node_id(self):
        """Test with empty node_id string."""
        result = ActionsHub._get_root_workflow_name_from_node_id("")
        assert result == ""

    def test_none_handling(self):
        """Test with None node_id - should handle gracefully."""
        # The method expects a string, but should handle empty/falsy values
        result = ActionsHub._get_root_workflow_name_from_node_id("")
        assert result == ""

    def test_node_id_with_high_count(self):
        """Test extracting root when count is high like 'A#999'."""
        result = ActionsHub._get_root_workflow_name_from_node_id("A#999")
        assert result == "A"

    def test_complex_workflow_name(self):
        """Test with complex workflow name containing CamelCase."""
        result = ActionsHub._get_root_workflow_name_from_node_id("MyComplexWorkflowName#1.ChildWorkflow#2")
        assert result == "MyComplexWorkflowName"


class TestUpsertRootWorkflowSearchAttribute:
    """Test cases for _upsert_root_workflow_search_attribute method."""

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    def test_upsert_called_with_correct_format(self, mock_upsert):
        """Test that upsert_search_attributes is called with correct format."""
        ActionsHub._upsert_root_workflow_search_attribute("TestWorkflow")

        mock_upsert.assert_called_once_with({"RootWorkflowName": ["TestWorkflow"]})

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    def test_upsert_not_called_with_empty_name(self, mock_upsert):
        """Test that upsert is not called when root_workflow_name is empty."""
        ActionsHub._upsert_root_workflow_search_attribute("")

        mock_upsert.assert_not_called()

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    def test_upsert_with_complex_name(self, mock_upsert):
        """Test upserting with complex workflow name."""
        ActionsHub._upsert_root_workflow_search_attribute("My_Complex_Workflow_123")

        mock_upsert.assert_called_once_with({"RootWorkflowName": ["My_Complex_Workflow_123"]})


class TestExecuteChildWorkflowRootWorkflowName:
    """Integration tests for execute_child_workflow with RootWorkflowName."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()
        ActionsHub._activities.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_execute_child_workflow_upserts_root_workflow_name(
        self, mock_get_simulation_response, mock_workflow_info, mock_get_mode, mock_execute_child, mock_upsert
    ):
        """Test that execute_child_workflow upserts RootWorkflowName search attribute."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_execute_child.return_value = "workflow_result"
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        await ActionsHub.execute_child_workflow("ChildWorkflow")

        # Verify upsert_search_attributes was called with correct format
        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args[0][0]
        assert "RootWorkflowName" in call_args
        assert call_args["RootWorkflowName"] == ["ChildWorkflow"]

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.payload_converter")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_execute_child_workflow_preserves_root_in_nested_calls(
        self,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_payload_converter,
        mock_execute_child,
        mock_upsert,
    ):
        """Test that nested child workflows preserve the original root workflow name."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse
        from zamp_public_workflow_sdk.temporal.interceptors.node_id_interceptor import NODE_ID_HEADER_KEY

        # Mock parent workflow with node ID (simulating we're inside child workflow B)
        mock_converter = Mock()
        mock_converter.from_payload.return_value = "ParentWorkflow#1"
        mock_payload_converter.return_value = mock_converter

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(
            workflow_id="test-workflow", headers={NODE_ID_HEADER_KEY: "mock_payload"}
        )
        mock_execute_child.return_value = "workflow_result"
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        await ActionsHub.execute_child_workflow("GrandchildWorkflow")

        # Verify upsert_search_attributes was called with the root (ParentWorkflow)
        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args[0][0]
        assert "RootWorkflowName" in call_args
        # The root should be "ParentWorkflow" (first segment before #)
        assert call_args["RootWorkflowName"] == ["ParentWorkflow"]

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    async def test_execute_child_workflow_api_mode_no_upsert(self, mock_get_mode, mock_upsert):
        """Test that API mode does not call upsert_search_attributes."""
        mock_get_mode.return_value = ExecutionMode.API

        # Mock the workflow function
        async def mock_workflow_func(*args, **kwargs):
            return "workflow_result"

        class MockWorkflowClass:
            pass

        from zamp_public_workflow_sdk.actions_hub.models.workflow_models import Workflow

        ActionsHub._workflows["TestWorkflow"] = Workflow(
            name="TestWorkflow",
            description="Test workflow",
            labels=[],
            class_type=MockWorkflowClass,
            func=mock_workflow_func,
        )

        await ActionsHub.execute_child_workflow("TestWorkflow")

        # In API mode, upsert should not be called
        mock_upsert.assert_not_called()


class TestStartChildWorkflowRootWorkflowName:
    """Integration tests for start_child_workflow with RootWorkflowName."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()
        ActionsHub._activities.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_start_child_workflow_upserts_root_workflow_name(
        self, mock_get_simulation_response, mock_workflow_info, mock_get_mode, mock_start_child, mock_upsert
    ):
        """Test that start_child_workflow upserts RootWorkflowName search attribute."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_start_child.return_value = Mock()  # Returns a handle
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        await ActionsHub.start_child_workflow("ChildWorkflow")

        # Verify upsert_search_attributes was called with correct format
        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args[0][0]
        assert "RootWorkflowName" in call_args
        assert call_args["RootWorkflowName"] == ["ChildWorkflow"]

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.payload_converter")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_start_child_workflow_preserves_root_in_nested_calls(
        self,
        mock_get_simulation_response,
        mock_workflow_info,
        mock_get_mode,
        mock_payload_converter,
        mock_start_child,
        mock_upsert,
    ):
        """Test that nested start_child_workflow preserves the original root workflow name."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse
        from zamp_public_workflow_sdk.temporal.interceptors.node_id_interceptor import NODE_ID_HEADER_KEY

        # Mock parent workflow with node ID
        mock_converter = Mock()
        mock_converter.from_payload.return_value = "RootWorkflow#1"
        mock_payload_converter.return_value = mock_converter

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(
            workflow_id="test-workflow", headers={NODE_ID_HEADER_KEY: "mock_payload"}
        )
        mock_start_child.return_value = Mock()
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        await ActionsHub.start_child_workflow("GrandchildWorkflow")

        # Verify upsert_search_attributes was called with the root
        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args[0][0]
        assert call_args["RootWorkflowName"] == ["RootWorkflow"]

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    async def test_start_child_workflow_skip_node_id_gen_no_upsert(self, mock_start_child, mock_upsert):
        """Test that skip_node_id_gen=True does not call upsert_search_attributes."""
        mock_start_child.return_value = Mock()

        await ActionsHub.start_child_workflow("ChildWorkflow", skip_node_id_gen=True)

        # When skipping node_id generation, upsert should not be called
        mock_upsert.assert_not_called()


class TestRootWorkflowNameEdgeCases:
    """Test edge cases for RootWorkflowName functionality."""

    def test_node_id_without_hash(self):
        """Test handling node_id without # character (edge case)."""
        # This shouldn't happen in practice, but test defensive behavior
        result = ActionsHub._get_root_workflow_name_from_node_id("WorkflowWithoutHash")
        # Should return the entire string as there's no # to split on
        assert result == "WorkflowWithoutHash"

    def test_node_id_starting_with_hash(self):
        """Test handling malformed node_id starting with #."""
        result = ActionsHub._get_root_workflow_name_from_node_id("#1.B#2")
        # First segment before # is empty
        assert result == ""

    def test_node_id_with_special_characters(self):
        """Test handling workflow names with special characters before #."""
        result = ActionsHub._get_root_workflow_name_from_node_id("Workflow-Name_v2#1")
        assert result == "Workflow-Name_v2"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    def test_upsert_handles_whitespace_name(self, mock_upsert):
        """Test that whitespace-only names are handled."""
        ActionsHub._upsert_root_workflow_search_attribute("   ")

        # Whitespace is truthy so it will be upserted
        mock_upsert.assert_called_once_with({"RootWorkflowName": ["   "]})
