"""
Unit tests for ActionsHub node ID generation and tracking functionality.

This module tests the new node ID system introduced in the fixPR-NodeIDRevamp branch.
"""

from __future__ import annotations

import threading
from unittest.mock import Mock, patch

import pytest

from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode
from zamp_public_workflow_sdk.temporal.interceptors.node_id_interceptor import NODE_ID_HEADER_KEY


# Global test classes for workflow tests
class TestWorkflowClass:
    @ActionsHub.register_workflow_run
    async def run(self) -> str:
        return "workflow_result"


class TestActionsHubNodeIdGeneration:
    """Test cases for ActionsHub node ID generation functionality."""

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

    def test_get_action_name_with_string(self):
        """Test _get_action_name with string input."""
        action_name = "test_activity"
        result = ActionsHub._get_action_name(action_name)
        assert result == "test_activity"

    def test_get_action_name_with_function(self):
        """Test _get_action_name with function input."""

        def test_function():
            pass

        result = ActionsHub._get_action_name(test_function)
        # Function defined inside test method gets the test class name
        assert result == "TestActionsHubNodeIdGeneration"

    def test_get_action_name_with_bound_method(self):
        """Test _get_action_name with bound method."""

        class TestClass:
            def test_method(self):
                pass

        instance = TestClass()
        result = ActionsHub._get_action_name(instance.test_method)
        assert result == "TestClass"

    def test_get_action_name_with_unbound_method(self):
        """Test _get_action_name with unbound method."""

        class TestClass:
            def test_method(self):
                pass

        result = ActionsHub._get_action_name(TestClass.test_method)
        # Unbound method defined inside test method gets the test class name
        assert result == "TestActionsHubNodeIdGeneration"

    def test_get_action_name_with_class_method(self):
        """Test _get_action_name with class method."""

        class TestClass:
            @classmethod
            def test_class_method(cls):
                pass

        result = ActionsHub._get_action_name(TestClass.test_class_method)
        # Class method returns 'type' for the class object
        assert result == "type"

    def test_get_action_name_with_static_method(self):
        """Test _get_action_name with static method."""

        class TestClass:
            @staticmethod
            def test_static_method():
                pass

        result = ActionsHub._get_action_name(TestClass.test_static_method)
        # Static method defined inside test method gets the test class name
        assert result == "TestActionsHubNodeIdGeneration"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    def test_get_current_workflow_id_workflow_mode(self, mock_get_mode, mock_workflow_info):
        """Test _get_current_workflow_id in workflow mode."""
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow-123")

        result = ActionsHub._get_current_workflow_id()
        assert result == "test-workflow-123"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context")
    def test_get_current_workflow_id_api_mode(self, mock_get_variable, mock_get_mode):
        """Test _get_current_workflow_id in API mode."""
        mock_get_mode.return_value = ExecutionMode.API
        mock_get_variable.return_value = "test-request-456"

        result = ActionsHub._get_current_workflow_id()
        assert result == "test-request-456"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    def test_get_current_workflow_id_workflow_exception(self, mock_get_mode, mock_workflow_info):
        """Test _get_current_workflow_id when workflow.info() raises exception."""
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.side_effect = Exception("Workflow not available")

        result = ActionsHub._get_current_workflow_id()
        assert result == "default"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_get_node_id_basic_generation(self, mock_workflow_info):
        """Test basic node ID generation without parent node ID."""
        mock_workflow_info.return_value = Mock(headers=None)

        result = ActionsHub._get_node_id("test-workflow", "TestActivity")
        assert result == "TestActivity#1"

        # Test multiple calls for same action
        result2 = ActionsHub._get_node_id("test-workflow", "TestActivity")
        assert result2 == "TestActivity#2"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.payload_converter")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_get_node_id_with_parent_node_id(self, mock_workflow_info, mock_payload_converter):
        """Test node ID generation with parent node ID."""
        # Mock the payload converter
        mock_converter = Mock()
        mock_converter.from_payload.return_value = "ParentWorkflow#1"
        mock_payload_converter.return_value = mock_converter

        mock_workflow_info.return_value = Mock(headers={NODE_ID_HEADER_KEY: "mock_payload"})

        result = ActionsHub._get_node_id("test-workflow", "TestActivity")
        assert result == "ParentWorkflow#1.TestActivity#1"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_get_node_id_thread_safety(self, mock_workflow_info):
        """Test thread safety of node ID generation."""
        mock_workflow_info.return_value = Mock(headers=None)

        results = []

        def generate_node_id():
            result = ActionsHub._get_node_id("test-workflow", "TestActivity")
            results.append(result)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=generate_node_id)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that all node IDs are unique
        assert len(set(results)) == 5
        assert all(result.startswith("TestActivity#") for result in results)

    def test_get_node_id_tracker_state(self):
        """Test getting node ID tracker state."""
        # Generate some node IDs to populate the tracker
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_workflow_info:
            mock_workflow_info.return_value = Mock(headers=None)

            ActionsHub._get_node_id("workflow1", "Activity1")
            ActionsHub._get_node_id("workflow1", "Activity1")
            ActionsHub._get_node_id("workflow2", "Activity2")

        state = ActionsHub.get_node_id_tracker_state()

        assert "workflow1" in state
        assert "workflow2" in state
        assert state["workflow1"]["Activity1"] == 2
        assert state["workflow2"]["Activity2"] == 1

    def test_clear_node_id_tracker(self):
        """Test clearing the node ID tracker."""
        # Generate some node IDs to populate the tracker
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_workflow_info:
            mock_workflow_info.return_value = Mock(headers=None)

            ActionsHub._get_node_id("workflow1", "Activity1")

        # Verify tracker has data
        state = ActionsHub.get_node_id_tracker_state()
        assert len(state) > 0

        # Clear tracker
        ActionsHub.clear_node_id_tracker()

        # Verify tracker is empty
        state = ActionsHub.get_node_id_tracker_state()
        assert len(state) == 0

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_current_workflow_id")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_node_id")
    def test_generate_node_id_for_action_success(self, mock_get_node_id, mock_get_workflow_id):
        """Test successful node ID generation for action."""
        mock_get_workflow_id.return_value = "test-workflow"
        mock_get_node_id.return_value = "TestActivity#1"

        action_name, workflow_id, node_id = ActionsHub._generate_node_id_for_action("test_activity")

        assert action_name == "test_activity"
        assert workflow_id == "test-workflow"
        assert node_id == "TestActivity#1"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_current_workflow_id")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_node_id")
    def test_generate_node_id_for_action_with_function(self, mock_get_node_id, mock_get_workflow_id):
        """Test node ID generation for action with function input."""

        def test_function():
            pass

        mock_get_workflow_id.return_value = "test-workflow"
        mock_get_node_id.return_value = "TestActionsHubNodeIdGeneration#1"

        action_name, workflow_id, node_id = ActionsHub._generate_node_id_for_action(test_function)

        assert action_name == "TestActionsHubNodeIdGeneration"
        assert workflow_id == "test-workflow"
        assert node_id == "TestActionsHubNodeIdGeneration#1"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_current_workflow_id")
    def test_generate_node_id_for_action_exception(self, mock_get_workflow_id):
        """Test node ID generation when exception occurs."""
        mock_get_workflow_id.side_effect = Exception("Test exception")

        with pytest.raises(Exception, match="Test exception"):
            ActionsHub._generate_node_id_for_action("test_activity")


class TestActionsHubNodeIdIntegration:
    """Integration tests for ActionsHub node ID functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()
        # Clear activities to avoid conflicts
        ActionsHub._activities.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_activity")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    async def test_execute_activity_with_node_id(self, mock_workflow_info, mock_get_mode, mock_execute_activity):
        """Test execute_activity generates and uses node ID."""
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_execute_activity.return_value = "activity_result"

        # Register a test activity
        @ActionsHub.register_activity("Test activity")
        def test_activity() -> str:
            return "test_result"

        await ActionsHub.execute_activity("test_activity")

        # Verify node ID was generated and used
        mock_execute_activity.assert_called_once()
        call_args = mock_execute_activity.call_args

        # Check that node_id was passed in args
        assert len(call_args[1]["args"]) > 0
        node_id_arg = call_args[1]["args"][0]
        assert "__temporal_node_id" in node_id_arg
        assert node_id_arg["__temporal_node_id"].startswith("test_activity#")

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    async def test_execute_child_workflow_with_node_id(self, mock_workflow_info, mock_get_mode, mock_execute_child):
        """Test execute_child_workflow generates and uses node ID."""
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_execute_child.return_value = "workflow_result"

        await ActionsHub.execute_child_workflow("TestWorkflow")

        # Verify node ID was generated and used
        mock_execute_child.assert_called_once()
        call_args = mock_execute_child.call_args

        # Check that node_id was passed in args
        assert len(call_args[1]["args"]) > 0
        node_id_arg = call_args[1]["args"][0]
        assert "__temporal_node_id" in node_id_arg
        assert node_id_arg["__temporal_node_id"].startswith("TestWorkflow#")

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    async def test_execute_activity_api_mode(self, mock_workflow_info, mock_get_mode):
        """Test execute_activity in API mode bypasses Temporal."""
        mock_get_mode.return_value = ExecutionMode.API
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)

        # Register a test activity
        @ActionsHub.register_activity("Test activity")
        def test_activity() -> str:
            return "test_result"

        result = await ActionsHub.execute_activity("test_activity")

        # Should return the direct result without Temporal
        assert result == "test_result"

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    async def test_execute_child_workflow_api_mode(self, mock_workflow_info, mock_get_mode):
        """Test execute_child_workflow in API mode bypasses Temporal."""
        mock_get_mode.return_value = ExecutionMode.API
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)

        # Mock the workflow function
        async def mock_workflow_func(*args, **kwargs):
            return "workflow_result"

        # Create a simple class for the workflow
        class MockWorkflowClass:
            pass

        # Register the workflow manually
        from zamp_public_workflow_sdk.actions_hub.models.workflow_models import Workflow

        ActionsHub._workflows["TestWorkflow"] = Workflow(
            name="TestWorkflow",
            description="Test workflow",
            labels=[],
            class_type=MockWorkflowClass,
            func=mock_workflow_func,
        )

        result = await ActionsHub.execute_child_workflow("TestWorkflow")

        # Should return the direct result without Temporal
        assert result == "workflow_result"

    def test_node_id_hierarchy_generation(self):
        """Test hierarchical node ID generation for nested workflows."""
        with (
            patch(
                "zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.payload_converter"
            ) as mock_payload_converter,
            patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_workflow_info,
        ):
            # Mock parent workflow with node ID
            mock_converter = Mock()
            mock_converter.from_payload.return_value = "ParentWorkflow#1"
            mock_payload_converter.return_value = mock_converter

            mock_workflow_info.return_value = Mock(headers={NODE_ID_HEADER_KEY: "mock_payload"})

            # Generate node ID for child activity
            result = ActionsHub._get_node_id("test-workflow", "ChildActivity")
            assert result == "ParentWorkflow#1.ChildActivity#1"

            # Generate another node ID for same child activity
            result2 = ActionsHub._get_node_id("test-workflow", "ChildActivity")
            assert result2 == "ParentWorkflow#1.ChildActivity#2"

    def test_multiple_workflows_node_id_tracking(self):
        """Test node ID tracking across multiple workflows."""
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_workflow_info:
            mock_workflow_info.return_value = Mock(headers=None)

            # Generate node IDs for different workflows
            result1 = ActionsHub._get_node_id("workflow1", "Activity1")
            result2 = ActionsHub._get_node_id("workflow2", "Activity1")
            result3 = ActionsHub._get_node_id("workflow1", "Activity2")

            assert result1 == "Activity1#1"
            assert result2 == "Activity1#1"  # Different workflow, resets counter
            assert result3 == "Activity2#1"

            # Check tracker state
            state = ActionsHub.get_node_id_tracker_state()
            assert state["workflow1"]["Activity1"] == 1
            assert state["workflow1"]["Activity2"] == 1
            assert state["workflow2"]["Activity1"] == 1


class TestActionsHubNodeIdEdgeCases:
    """Test edge cases and error conditions for node ID functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()
        # Clear activities to avoid conflicts
        ActionsHub._activities.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.payload_converter")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_get_node_id_with_empty_parent_node_id(self, mock_workflow_info, mock_payload_converter):
        """Test node ID generation when parent node ID is empty."""
        mock_converter = Mock()
        mock_converter.from_payload.return_value = None
        mock_payload_converter.return_value = mock_converter

        mock_workflow_info.return_value = Mock(headers={NODE_ID_HEADER_KEY: "mock_payload"})

        result = ActionsHub._get_node_id("test-workflow", "TestActivity")
        assert result == "TestActivity#1"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_get_node_id_with_missing_headers(self, mock_workflow_info):
        """Test node ID generation when headers are missing."""
        mock_workflow_info.return_value = Mock(headers=None)

        result = ActionsHub._get_node_id("test-workflow", "TestActivity")
        assert result == "TestActivity#1"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_get_node_id_with_missing_node_id_header(self, mock_workflow_info):
        """Test node ID generation when NODE_ID_HEADER_KEY is missing from headers."""
        mock_workflow_info.return_value = Mock(headers={"other_header": "value"})

        result = ActionsHub._get_node_id("test-workflow", "TestActivity")
        assert result == "TestActivity#1"

    def test_get_action_name_with_lambda(self):
        """Test _get_action_name with lambda function."""

        def lambda_func(x):
            return x * 2

        result = ActionsHub._get_action_name(lambda_func)
        # Lambda defined inside test method gets the test class name
        assert result == "TestActionsHubNodeIdEdgeCases"

    def test_get_action_name_with_builtin_function(self):
        """Test _get_action_name with builtin function."""
        result = ActionsHub._get_action_name(len)
        # Builtin function returns the module name
        assert result == "module"

    def test_get_action_name_with_nested_qualname(self):
        """Test _get_action_name with deeply nested qualname."""

        class OuterClass:
            class InnerClass:
                def nested_method(self):
                    pass

        instance = OuterClass.InnerClass()
        result = ActionsHub._get_action_name(instance.nested_method)
        assert result == "InnerClass"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_concurrent_node_id_generation_same_workflow(self, mock_workflow_info):
        """Test concurrent node ID generation for same workflow and action."""
        mock_workflow_info.return_value = Mock(headers=None)

        results = []
        errors = []

        def generate_node_id():
            try:
                result = ActionsHub._get_node_id("test-workflow", "TestActivity")
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=generate_node_id)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0

        # Should have 10 unique results
        assert len(results) == 10
        assert len(set(results)) == 10

        # All should be TestActivity#N format
        for result in results:
            assert result.startswith("TestActivity#")
            assert result.split("#")[1].isdigit()

    def test_node_id_tracker_persistence_across_calls(self):
        """Test that node ID tracker persists state across multiple calls."""
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_workflow_info:
            mock_workflow_info.return_value = Mock(headers=None)

            # First call
            result1 = ActionsHub._get_node_id("test-workflow", "TestActivity")
            assert result1 == "TestActivity#1"

            # Second call
            result2 = ActionsHub._get_node_id("test-workflow", "TestActivity")
            assert result2 == "TestActivity#2"

            # Third call with different action
            result3 = ActionsHub._get_node_id("test-workflow", "OtherActivity")
            assert result3 == "OtherActivity#1"

            # Fourth call with first action again
            result4 = ActionsHub._get_node_id("test-workflow", "TestActivity")
            assert result4 == "TestActivity#3"

            # Check final state
            state = ActionsHub.get_node_id_tracker_state()
            assert state["test-workflow"]["TestActivity"] == 3
            assert state["test-workflow"]["OtherActivity"] == 1
