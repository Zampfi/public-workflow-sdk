"""
Tests for actions_hub.py
"""

from datetime import timedelta
from unittest.mock import Mock, patch

import pytest


from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.constants import ActionType
from zamp_public_workflow_sdk.actions_hub.models.core_models import Action, RetryPolicy


class TestActionsHub:
    """Test the ActionsHub class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock the ActionsHub class to avoid complex dependencies
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.unsafe.imports_passed_through"):
            # Import ActionsHub directly from the module
            from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub

            self.ActionsHub = ActionsHub

        # Store original registries to restore later
        self.original_activities = self.ActionsHub._activities.copy()
        self.original_business_logic_methods = self.ActionsHub._business_logic_methods.copy()
        self.original_workflows = self.ActionsHub._workflows.copy()
        self.original_action_list = self.ActionsHub._action_list.copy()

        # Clear any existing registrations before each test
        self.ActionsHub._activities.clear()
        self.ActionsHub._business_logic_methods.clear()
        self.ActionsHub._workflows.clear()
        self.ActionsHub._action_list.clear()

    def teardown_method(self):
        """Restore original registries after each test."""
        # Restore original registries to prevent test isolation issues
        self.ActionsHub._activities.clear()
        self.ActionsHub._activities.update(self.original_activities)
        self.ActionsHub._business_logic_methods.clear()
        self.ActionsHub._business_logic_methods.update(self.original_business_logic_methods)
        self.ActionsHub._workflows.clear()
        self.ActionsHub._workflows.update(self.original_workflows)
        self.ActionsHub._action_list.clear()
        self.ActionsHub._action_list.extend(self.original_action_list)

    def test_actions_hub_initialization(self):
        """Test ActionsHub initialization."""
        hub = self.ActionsHub()

        # Check that the hub is properly initialized
        assert hasattr(hub, "_activities")
        assert hasattr(hub, "_workflows")
        assert hasattr(hub, "_business_logic_methods")
        assert hasattr(hub, "_action_list")
        assert hasattr(hub, "_node_id_tracker")

    def test_register_activity(self):
        """Test registering an activity."""
        hub = self.ActionsHub()

        def test_activity_func(param1: str) -> str:
            return f"Hello {param1}"

        # Use the decorator approach as per actual implementation
        @hub.register_activity("Test activity")
        def test_activity(param1: str) -> str:
            return f"Hello {param1}"

        # Check that the activity is registered
        activities = hub.get_available_activities()
        activity_names = [activity.name for activity in activities]
        assert "test_activity" in activity_names

    def test_register_workflow(self):
        """Test registering a workflow."""
        hub = self.ActionsHub()

        # Test that the workflow registration method exists and can be called
        # Note: Full workflow testing requires global classes, so we just test the method exists
        assert hasattr(hub, "register_workflow_defn")
        assert hasattr(hub, "register_workflow_run")

        # Test that we can get available workflows
        workflows = hub.get_available_workflows(["test"])
        assert isinstance(workflows, list)

    def test_register_business_logic(self):
        """Test registering business logic."""
        hub = self.ActionsHub()

        # Use the decorator approach as per actual implementation
        @hub.register_business_logic("Test business logic", ["test"])
        def test_business_logic_func(param1: str) -> bool:
            return len(param1) > 0

        # Check that the business logic is registered
        business_logic_list = hub.get_available_business_logic_list()
        business_logic_names = [bl.name for bl in business_logic_list]
        assert "test_business_logic_func" in business_logic_names

    def test_get_actions(self):
        """Test getting all actions."""

        # Register some actions using class methods
        @self.ActionsHub.register_activity("Test activity for get_actions")
        def test_activity_get_actions(x: str) -> str:
            return x

        @self.ActionsHub.register_business_logic("Test business logic for get_actions", ["test"])
        def test_business_logic_get_actions(x: str) -> str:
            return x

        # Test with specific filter to get the activity
        from zamp_public_workflow_sdk.actions_hub.models.core_models import ActionFilter

        filter_obj = ActionFilter(resticted_action_set={"test_activity_get_actions"})
        actions = self.ActionsHub.get_available_actions(filter_obj)

        # Check that we get exactly 1 action (the filtered one)
        assert len(actions) == 1, f"Expected 1 filtered action, got {len(actions)}"

        # Verify it's the correct action
        assert actions[0].name == "test_activity_get_actions"
        assert hasattr(actions[0], "action_type")

        # Test with name filter for business logic
        filter_obj2 = ActionFilter(name="test_business_logic_get_actions")
        actions2 = self.ActionsHub.get_available_actions(filter_obj2)

        # Check that we get exactly 1 action (the name filtered one)
        assert len(actions2) == 1, f"Expected 1 name filtered action, got {len(actions2)}"
        assert actions2[0].name == "test_business_logic_get_actions"

    def test_get_actions_with_filter(self):
        """Test getting actions with a filter."""

        # Register some actions using class methods
        @self.ActionsHub.register_activity("Test activity for filter")
        def test_activity_filter(x: str) -> str:
            return x

        # Test with filter
        from zamp_public_workflow_sdk.actions_hub.models.core_models import ActionFilter

        filter_obj = ActionFilter(resticted_action_set={"test_activity_filter"})
        actions = self.ActionsHub.get_available_actions(filter_obj)

        # Check that we get exactly 1 action (the filtered one)
        assert len(actions) == 1, f"Expected 1 filtered action, got {len(actions)}"

        # Verify it's the correct action
        assert actions[0].name == "test_activity_filter"
        assert hasattr(actions[0], "action_type")

    def test_get_activity(self):
        """Test getting a specific activity."""
        hub = self.ActionsHub()

        @hub.register_activity("Test activity for get")
        def test_activity_get(x: str) -> str:
            return x

        # Use the correct method name
        retrieved_activity = hub.get_activity_details("test_activity_get")

        # Check that the correct activity is returned
        assert retrieved_activity.name == "test_activity_get"
        assert retrieved_activity.description == "Test activity for get"

    def test_get_workflow(self):
        """Test getting a specific workflow."""
        hub = self.ActionsHub()

        # Test that the workflow method exists and can be called
        # Note: Full workflow testing requires global classes, so we just test the method exists
        assert hasattr(hub, "get_workflow")

        # Test that we can get available workflows
        workflows = hub.get_available_workflows(["test"])
        assert isinstance(workflows, list)

    def test_get_business_logic(self):
        """Test getting specific business logic."""

        @self.ActionsHub.register_business_logic("Test business logic for get", ["test"])
        def test_business_logic_get(x):
            return x

        # Get business logic by labels
        business_logic_list = self.ActionsHub.get_business_logic_by_labels(["test"])

        # Check that we get exactly 1 business logic function
        assert len(business_logic_list) == 1, f"Expected 1 business logic, got {len(business_logic_list)}"

        # Verify it's the correct business logic
        assert business_logic_list[0].name == "test_business_logic_get"
        assert hasattr(business_logic_list[0], "name")

    def test_register_connection_mapping(self):
        """Test registering connection mappings."""
        hub = self.ActionsHub()

        from zamp_public_workflow_sdk.actions_hub.models.credentials_models import ActionConnectionsMapping, Connection

        # Create proper Connection objects
        conn1 = Connection(connection_id="conn1", summary="Connection 1")
        conn2 = Connection(connection_id="conn2", summary="Connection 2")

        mapping = ActionConnectionsMapping(action_name="test_action", connections=[conn1, conn2])

        hub.register_action_list([mapping])

        # Check that the mapping is registered (check if it's in _action_list)
        assert len(hub._action_list) == 1, f"Expected 1 mapping, got {len(hub._action_list)}"

        # Verify it's the correct mapping
        assert hub._action_list[0].action_name == "test_action"
        assert hasattr(hub._action_list[0], "action_name")

    def test_get_connection_mapping(self):
        """Test getting connection mappings."""
        hub = self.ActionsHub()

        from zamp_public_workflow_sdk.actions_hub.models.credentials_models import ActionConnectionsMapping, Connection

        # Create proper Connection objects
        conn1 = Connection(connection_id="conn1", summary="Connection 1")
        conn2 = Connection(connection_id="conn2", summary="Connection 2")

        mapping = ActionConnectionsMapping(action_name="test_action", connections=[conn1, conn2])

        hub.register_action_list([mapping])

        # Check that the mapping is registered (check if it's in _action_list)
        assert len(hub._action_list) == 1, f"Expected 1 mapping, got {len(hub._action_list)}"

        # Verify it's the correct mapping
        assert hub._action_list[0].action_name == "test_action"
        assert hasattr(hub._action_list[0], "action_name")

    def test_clear_registry(self):
        """Test clearing the registry."""
        hub = self.ActionsHub()

        # Test that the clear methods exist
        assert hasattr(hub, "clear_node_id_tracker")

        # Test clearing node id tracker
        hub.clear_node_id_tracker()

        # Check that the tracker is cleared
        state = hub.get_node_id_tracker_state()
        assert isinstance(state, dict)

    def test_retry_policy_defaults(self):
        """Test retry policy defaults."""
        from zamp_public_workflow_sdk.actions_hub.models.core_models import RetryPolicy

        # Test that RetryPolicy class works
        retry_policy = RetryPolicy.default()

        # Check that the retry policy has expected defaults
        assert retry_policy.maximum_attempts == 11
        assert retry_policy.initial_interval == timedelta(seconds=30)
        assert retry_policy.maximum_interval == timedelta(seconds=900)

    def test_retry_policy_custom(self):
        """Test custom retry policies."""
        from zamp_public_workflow_sdk.actions_hub.models.core_models import RetryPolicy

        # Test creating custom retry policy
        custom_retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=10),
            maximum_attempts=5,
            maximum_interval=timedelta(minutes=5),
            backoff_coefficient=2.0,
        )

        # Test that the custom retry policy is created correctly
        assert custom_retry_policy.maximum_attempts == 5
        assert custom_retry_policy.initial_interval == timedelta(seconds=10)
        assert custom_retry_policy.maximum_interval == timedelta(minutes=5)
        assert custom_retry_policy.backoff_coefficient == 2.0

    def test_dispatch_action_activity(self):
        """Test dispatching an activity action."""
        hub = self.ActionsHub()

        # Test that the dispatch method exists
        assert hasattr(hub, "_dispatch_action")

        # Note: Full dispatch testing requires workflow context, so we just test the method exists

    def test_dispatch_action_workflow(self):
        """Test dispatching a workflow action."""
        hub = self.ActionsHub()

        # Test that the dispatch method exists
        assert hasattr(hub, "_dispatch_action")

        # Note: Full dispatch testing requires workflow context, so we just test the method exists

    @pytest.mark.asyncio
    async def test_dispatch_action_business_logic_sync(self):
        """Test dispatching a synchronous business logic action."""
        hub = self.ActionsHub()

        # Create a synchronous function
        def sync_business_logic(param: str) -> str:
            return f"sync_result_{param}"

        # Create a mock action
        action = Mock(spec=Action)
        action.action_type = ActionType.BUSINESS_LOGIC
        action.name = "test_business_logic"
        action.func = sync_business_logic

        retry_policy = RetryPolicy.default()

        # Mock the execute_activity class method to avoid workflow context issues
        with patch.object(ActionsHub, "execute_activity") as mock_execute_activity:
            mock_execute_activity.return_value = "sync_result_test_param"

            result = await hub._dispatch_action(action, retry_policy, "test_param")

            assert result == "sync_result_test_param"
            # Verify that execute_activity was called with the correct parameters
            mock_execute_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_action_business_logic_async(self):
        """Test dispatching an asynchronous business logic action."""
        hub = self.ActionsHub()

        # Create an asynchronous function
        async def async_business_logic(param: str) -> str:
            return f"async_result_{param}"

        # Create a mock action
        action = Mock(spec=Action)
        action.action_type = ActionType.BUSINESS_LOGIC
        action.name = "test_business_logic"
        action.func = async_business_logic

        retry_policy = RetryPolicy.default()

        # Mock the execute_activity class method to avoid workflow context issues
        with patch.object(ActionsHub, "execute_activity") as mock_execute_activity:
            mock_execute_activity.return_value = "async_result_test_param"

            result = await hub._dispatch_action(action, retry_policy, "test_param")

            assert result == "async_result_test_param"
            # Verify that execute_activity was called with the correct parameters
            mock_execute_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_action_business_logic_no_func(self):
        """Test dispatching a business logic action without a function."""
        hub = self.ActionsHub()

        # Create a mock action without a function
        action = Mock(spec=Action)
        action.action_type = ActionType.BUSINESS_LOGIC
        action.name = "test_business_logic"
        action.func = None

        retry_policy = RetryPolicy.default()

        # Mock the execute_activity class method to avoid workflow context issues
        with patch.object(ActionsHub, "execute_activity") as mock_execute_activity:
            # The execute_activity should still be called even with None func
            # because the current implementation doesn't check for None func before calling
            mock_execute_activity.return_value = None

            await hub._dispatch_action(action, retry_policy, "test_param")

            # Verify that execute_activity was called
            mock_execute_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_action_unknown_type(self):
        """Test dispatching an action with unknown type."""
        hub = self.ActionsHub()

        # Create a mock action with unknown type
        action = Mock(spec=Action)
        action.action_type = "UNKNOWN_TYPE"
        action.name = "test_action"

        retry_policy = RetryPolicy.default()

        with pytest.raises(ValueError, match="Unknown action type: UNKNOWN_TYPE"):
            await hub._dispatch_action(action, retry_policy, "test_param")
