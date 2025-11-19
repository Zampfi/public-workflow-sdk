"""
Tests for ActionsHub continue_as_new method.

This module tests the continue_as_new functionality exposed through ActionsHub.
"""

from datetime import timedelta
from unittest.mock import Mock, patch

import pytest

from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub


class TestActionsHubContinueAsNew:
    """Test cases for ActionsHub continue_as_new functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear any existing state
        ActionsHub.clear_node_id_tracker()
        ActionsHub._activities.clear()
        ActionsHub._workflows.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_no_args(self, mock_continue_as_new):
        """Test continue_as_new with no arguments."""
        # Mock the workflow.continue_as_new to avoid workflow context issues
        mock_continue_as_new.return_value = None

        # Call the method
        ActionsHub.continue_as_new()

        # Verify workflow.continue_as_new was called with no arguments
        mock_continue_as_new.assert_called_once_with()

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_positional_args(self, mock_continue_as_new):
        """Test continue_as_new with positional arguments."""
        mock_continue_as_new.return_value = None

        # Call with positional arguments
        ActionsHub.continue_as_new("arg1", "arg2", 123)

        # Verify workflow.continue_as_new was called with the correct arguments
        mock_continue_as_new.assert_called_once_with("arg1", "arg2", 123)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_keyword_args(self, mock_continue_as_new):
        """Test continue_as_new with keyword arguments."""
        mock_continue_as_new.return_value = None

        # Call with keyword arguments
        ActionsHub.continue_as_new(task_queue="my-queue", run_timeout=timedelta(hours=1))

        # Verify workflow.continue_as_new was called with the correct keyword arguments
        mock_continue_as_new.assert_called_once_with(task_queue="my-queue", run_timeout=timedelta(hours=1))

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_mixed_args(self, mock_continue_as_new):
        """Test continue_as_new with both positional and keyword arguments."""
        mock_continue_as_new.return_value = None

        # Call with both positional and keyword arguments
        ActionsHub.continue_as_new(
            "arg1",
            42,
            task_queue="test-queue",
            run_timeout=timedelta(minutes=30),
        )

        # Verify workflow.continue_as_new was called correctly
        mock_continue_as_new.assert_called_once_with(
            "arg1",
            42,
            task_queue="test-queue",
            run_timeout=timedelta(minutes=30),
        )

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_workflow_param(self, mock_continue_as_new):
        """Test continue_as_new with workflow parameter."""
        mock_continue_as_new.return_value = None

        # Mock workflow class
        class TestWorkflow:
            pass

        # Call with workflow parameter
        ActionsHub.continue_as_new("input_data", workflow=TestWorkflow)

        # Verify workflow.continue_as_new was called with workflow parameter
        mock_continue_as_new.assert_called_once_with("input_data", workflow=TestWorkflow)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_task_timeout(self, mock_continue_as_new):
        """Test continue_as_new with task_timeout parameter."""
        mock_continue_as_new.return_value = None

        timeout = timedelta(seconds=45)
        ActionsHub.continue_as_new(task_timeout=timeout)

        # Verify workflow.continue_as_new was called with task_timeout
        mock_continue_as_new.assert_called_once_with(task_timeout=timeout)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_memo(self, mock_continue_as_new):
        """Test continue_as_new with memo parameter."""
        mock_continue_as_new.return_value = None

        memo = {"key1": "value1", "key2": "value2"}
        ActionsHub.continue_as_new(memo=memo)

        # Verify workflow.continue_as_new was called with memo
        mock_continue_as_new.assert_called_once_with(memo=memo)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_search_attributes(self, mock_continue_as_new):
        """Test continue_as_new with search_attributes parameter."""
        mock_continue_as_new.return_value = None

        search_attrs = {"CustomKeywordField": ["value1", "value2"]}
        ActionsHub.continue_as_new(search_attributes=search_attrs)

        # Verify workflow.continue_as_new was called with search_attributes
        mock_continue_as_new.assert_called_once_with(search_attributes=search_attrs)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_retry_policy(self, mock_continue_as_new):
        """Test continue_as_new with retry_policy parameter."""
        mock_continue_as_new.return_value = None

        # Create a mock retry policy
        retry_policy = Mock()
        ActionsHub.continue_as_new(retry_policy=retry_policy)

        # Verify workflow.continue_as_new was called with retry_policy
        mock_continue_as_new.assert_called_once_with(retry_policy=retry_policy)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_all_params(self, mock_continue_as_new):
        """Test continue_as_new with all possible parameters."""
        mock_continue_as_new.return_value = None

        class TestWorkflow:
            pass

        memo = {"key": "value"}
        search_attrs = {"CustomField": ["test"]}
        retry_policy = Mock()

        ActionsHub.continue_as_new(
            "arg1",
            "arg2",
            workflow=TestWorkflow,
            task_queue="comprehensive-queue",
            run_timeout=timedelta(hours=2),
            task_timeout=timedelta(minutes=10),
            retry_policy=retry_policy,
            memo=memo,
            search_attributes=search_attrs,
        )

        # Verify workflow.continue_as_new was called with all parameters
        mock_continue_as_new.assert_called_once_with(
            "arg1",
            "arg2",
            workflow=TestWorkflow,
            task_queue="comprehensive-queue",
            run_timeout=timedelta(hours=2),
            task_timeout=timedelta(minutes=10),
            retry_policy=retry_policy,
            memo=memo,
            search_attributes=search_attrs,
        )

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_raises_exception(self, mock_continue_as_new):
        """Test continue_as_new when it raises an exception."""
        # Mock workflow.continue_as_new to raise a generic exception
        # (ContinueAsNewError cannot be instantiated directly in Temporal)
        mock_continue_as_new.side_effect = RuntimeError("Test exception during continue_as_new")

        # Call should raise RuntimeError
        with pytest.raises(RuntimeError, match="Test exception during continue_as_new"):
            ActionsHub.continue_as_new("test_arg")

        # Verify workflow.continue_as_new was called
        mock_continue_as_new.assert_called_once_with("test_arg")

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_method_exists(self, mock_continue_as_new):
        """Test that continue_as_new method exists and is callable."""
        # Verify the method exists
        assert hasattr(ActionsHub, "continue_as_new")
        assert callable(ActionsHub.continue_as_new)

        # Verify it's a classmethod
        import inspect

        assert isinstance(inspect.getattr_static(ActionsHub, "continue_as_new"), classmethod)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_dict_args(self, mock_continue_as_new):
        """Test continue_as_new with dictionary as argument."""
        mock_continue_as_new.return_value = None

        input_data = {"key1": "value1", "key2": 123, "nested": {"inner": "value"}}
        ActionsHub.continue_as_new(input_data)

        # Verify workflow.continue_as_new was called with the dict
        mock_continue_as_new.assert_called_once_with(input_data)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_list_args(self, mock_continue_as_new):
        """Test continue_as_new with list as argument."""
        mock_continue_as_new.return_value = None

        input_list = ["item1", "item2", "item3"]
        ActionsHub.continue_as_new(input_list)

        # Verify workflow.continue_as_new was called with the list
        mock_continue_as_new.assert_called_once_with(input_list)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_complex_types(self, mock_continue_as_new):
        """Test continue_as_new with complex type arguments."""
        mock_continue_as_new.return_value = None

        # Create a mock Pydantic model or complex object
        complex_obj = Mock()
        complex_obj.field1 = "value1"
        complex_obj.field2 = 42

        ActionsHub.continue_as_new(complex_obj, additional_param="test")

        # Verify workflow.continue_as_new was called with complex object
        mock_continue_as_new.assert_called_once_with(complex_obj, additional_param="test")

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_preserves_argument_order(self, mock_continue_as_new):
        """Test that continue_as_new preserves the order of positional arguments."""
        mock_continue_as_new.return_value = None

        ActionsHub.continue_as_new("first", "second", "third", "fourth")

        # Verify the order is preserved
        mock_continue_as_new.assert_called_once_with("first", "second", "third", "fourth")

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_none_values(self, mock_continue_as_new):
        """Test continue_as_new with None values."""
        mock_continue_as_new.return_value = None

        ActionsHub.continue_as_new(None, task_queue=None, memo=None)

        # Verify workflow.continue_as_new was called with None values
        mock_continue_as_new.assert_called_once_with(None, task_queue=None, memo=None)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_multiple_calls(self, mock_continue_as_new):
        """Test multiple calls to continue_as_new."""
        mock_continue_as_new.return_value = None

        # First call
        ActionsHub.continue_as_new("call1")
        # Second call
        ActionsHub.continue_as_new("call2")
        # Third call
        ActionsHub.continue_as_new("call3")

        # Verify workflow.continue_as_new was called three times
        assert mock_continue_as_new.call_count == 3

        # Verify each call had the correct argument
        calls = mock_continue_as_new.call_args_list
        assert calls[0][0] == ("call1",)
        assert calls[1][0] == ("call2",)
        assert calls[2][0] == ("call3",)


class TestActionsHubContinueAsNewIntegration:
    """Integration tests for continue_as_new with other ActionsHub features."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()
        ActionsHub._activities.clear()
        ActionsHub._workflows.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_with_workflow_sleep(self, mock_continue_as_new):
        """Test that continue_as_new and workflow_sleep can be used together."""
        mock_continue_as_new.return_value = None

        # Both methods should be available
        assert hasattr(ActionsHub, "continue_as_new")
        assert hasattr(ActionsHub, "workflow_sleep")

        # Test that continue_as_new can be called independently
        ActionsHub.continue_as_new("test_input")
        mock_continue_as_new.assert_called_once_with("test_input")

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_does_not_affect_node_id_tracker(self, mock_continue_as_new):
        """Test that continue_as_new doesn't modify node_id_tracker state."""
        mock_continue_as_new.return_value = None

        # Get initial state
        initial_state = ActionsHub.get_node_id_tracker_state()

        # Call continue_as_new
        ActionsHub.continue_as_new("test")

        # Get state after call
        final_state = ActionsHub.get_node_id_tracker_state()

        # State should be unchanged
        assert initial_state == final_state

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.continue_as_new")
    def test_continue_as_new_does_not_affect_registries(self, mock_continue_as_new):
        """Test that continue_as_new doesn't modify activity/workflow registries."""
        mock_continue_as_new.return_value = None

        # Register an activity
        @ActionsHub.register_activity("Test activity")
        def test_activity() -> str:
            return "test"

        # Get registry sizes
        activities_count = len(ActionsHub._activities)

        # Call continue_as_new
        ActionsHub.continue_as_new("test")

        # Verify registries are unchanged
        assert len(ActionsHub._activities) == activities_count

    def test_continue_as_new_in_workflow_context(self):
        """Test that continue_as_new is properly exposed in workflow context."""
        # This test verifies the method signature and availability
        # without requiring actual workflow execution

        import inspect

        # Get the method signature
        sig = inspect.signature(ActionsHub.continue_as_new)

        # Verify it accepts *args and **kwargs
        params = list(sig.parameters.values())

        # Should have 'cls' (implicit for classmethod), *args, and **kwargs
        param_kinds = [p.kind for p in params]

        # Check for VAR_POSITIONAL (*args) and VAR_KEYWORD (**kwargs)
        assert inspect.Parameter.VAR_POSITIONAL in param_kinds
        assert inspect.Parameter.VAR_KEYWORD in param_kinds
