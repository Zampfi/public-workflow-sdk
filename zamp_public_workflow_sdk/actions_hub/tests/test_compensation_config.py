"""
Tests for compensation configuration (Phase 1 of Saga Pattern Implementation).

Tests cover:
- CompensationActionType enum
- CompensationConfig model
- activity_compensation() and workflow_compensation() helper functions
- register_activity() with compensation parameter
- get_compensation_config() and has_compensation() methods
"""

import sys
import os

import pytest

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from zamp_public_workflow_sdk.actions_hub.constants import CompensationActionType
from zamp_public_workflow_sdk.actions_hub.models.compensation_models import (
    CompensationConfig,
    activity_compensation,
    workflow_compensation,
)
from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub


class TestCompensationActionType:
    """Test the CompensationActionType enum."""

    def test_enum_values(self):
        """Test CompensationActionType enum values."""
        assert CompensationActionType.ACTIVITY == "activity"
        assert CompensationActionType.WORKFLOW == "workflow"

    def test_enum_membership(self):
        """Test CompensationActionType enum membership."""
        assert CompensationActionType.ACTIVITY in CompensationActionType
        assert CompensationActionType.WORKFLOW in CompensationActionType

    def test_enum_string_representation(self):
        """Test CompensationActionType string representation."""
        assert CompensationActionType.ACTIVITY.value == "activity"
        assert CompensationActionType.WORKFLOW.value == "workflow"

    def test_enum_equality(self):
        """Test CompensationActionType equality comparisons."""
        assert CompensationActionType.ACTIVITY == CompensationActionType.ACTIVITY
        assert CompensationActionType.WORKFLOW == CompensationActionType.WORKFLOW
        assert CompensationActionType.ACTIVITY != CompensationActionType.WORKFLOW


class TestCompensationConfig:
    """Test the CompensationConfig model."""

    def test_compensation_config_creation_activity(self):
        """Test CompensationConfig creation with activity type."""
        config = CompensationConfig(
            action_type=CompensationActionType.ACTIVITY,
            action_name="delete_slack_message",
        )

        assert config.action_type == CompensationActionType.ACTIVITY
        assert config.action_name == "delete_slack_message"

    def test_compensation_config_creation_workflow(self):
        """Test CompensationConfig creation with workflow type."""
        config = CompensationConfig(
            action_type=CompensationActionType.WORKFLOW,
            action_name="PaymentRollbackWorkflow",
        )

        assert config.action_type == CompensationActionType.WORKFLOW
        assert config.action_name == "PaymentRollbackWorkflow"

    def test_compensation_config_validation_missing_action_type(self):
        """Test CompensationConfig validation for missing action_type."""
        with pytest.raises(Exception):  # Pydantic validation error
            CompensationConfig(action_name="test_action")

    def test_compensation_config_validation_missing_action_name(self):
        """Test CompensationConfig validation for missing action_name."""
        with pytest.raises(Exception):  # Pydantic validation error
            CompensationConfig(action_type=CompensationActionType.ACTIVITY)

    def test_compensation_config_serialization(self):
        """Test CompensationConfig serialization."""
        config = CompensationConfig(
            action_type=CompensationActionType.ACTIVITY,
            action_name="delete_user",
        )

        serialized = config.model_dump()
        assert serialized["action_type"] == "activity"
        assert serialized["action_name"] == "delete_user"


class TestCompensationHelperFunctions:
    """Test the compensation helper functions."""

    def test_activity_compensation_helper(self):
        """Test activity_compensation() helper function."""
        config = activity_compensation("delete_slack_message")

        assert isinstance(config, CompensationConfig)
        assert config.action_type == CompensationActionType.ACTIVITY
        assert config.action_name == "delete_slack_message"

    def test_workflow_compensation_helper(self):
        """Test workflow_compensation() helper function."""
        config = workflow_compensation("PaymentRollbackWorkflow")

        assert isinstance(config, CompensationConfig)
        assert config.action_type == CompensationActionType.WORKFLOW
        assert config.action_name == "PaymentRollbackWorkflow"

    def test_activity_compensation_with_various_names(self):
        """Test activity_compensation() with various action names."""
        test_names = [
            "delete_user",
            "rollback_transaction",
            "cancel_order",
            "remove_file",
        ]

        for name in test_names:
            config = activity_compensation(name)
            assert config.action_type == CompensationActionType.ACTIVITY
            assert config.action_name == name

    def test_workflow_compensation_with_various_names(self):
        """Test workflow_compensation() with various workflow names."""
        test_names = [
            "RollbackWorkflow",
            "CompensationWorkflow",
            "UndoChangesWorkflow",
            "CleanupWorkflow",
        ]

        for name in test_names:
            config = workflow_compensation(name)
            assert config.action_type == CompensationActionType.WORKFLOW
            assert config.action_name == name


class TestActionsHubCompensation:
    """Test ActionsHub compensation-related methods."""

    def setup_method(self):
        """Set up test fixtures."""
        # Store original registries to restore later
        self.original_activities = ActionsHub._activities.copy()

        # Clear any existing registrations before each test
        ActionsHub._activities.clear()

    def teardown_method(self):
        """Restore original registries after each test."""
        # Restore original registries to prevent test isolation issues
        ActionsHub._activities.clear()
        ActionsHub._activities.update(self.original_activities)

    def test_register_activity_without_compensation(self):
        """Test registering an activity without compensation."""

        @ActionsHub.register_activity("Test activity without compensation")
        def test_activity_no_comp(param1: str) -> str:
            return f"Hello {param1}"

        # Check that the activity is registered
        activity = ActionsHub.get_activity_by_name("test_activity_no_comp")
        assert activity is not None
        assert activity.name == "test_activity_no_comp"
        assert activity.compensation_config is None

    def test_register_activity_with_activity_compensation(self):
        """Test registering an activity with activity compensation."""
        compensation = activity_compensation("delete_test_data")

        @ActionsHub.register_activity(
            "Test activity with compensation",
            compensation=compensation,
        )
        def test_activity_with_comp(param1: str) -> str:
            return f"Hello {param1}"

        # Check that the activity is registered with compensation
        activity = ActionsHub.get_activity_by_name("test_activity_with_comp")
        assert activity is not None
        assert activity.compensation_config is not None
        assert activity.compensation_config.action_type == CompensationActionType.ACTIVITY
        assert activity.compensation_config.action_name == "delete_test_data"

    def test_register_activity_with_workflow_compensation(self):
        """Test registering an activity with workflow compensation."""
        compensation = workflow_compensation("RollbackWorkflow")

        @ActionsHub.register_activity(
            "Test activity with workflow compensation",
            compensation=compensation,
        )
        def test_activity_workflow_comp(param1: str) -> str:
            return f"Hello {param1}"

        # Check that the activity is registered with workflow compensation
        activity = ActionsHub.get_activity_by_name("test_activity_workflow_comp")
        assert activity is not None
        assert activity.compensation_config is not None
        assert activity.compensation_config.action_type == CompensationActionType.WORKFLOW
        assert activity.compensation_config.action_name == "RollbackWorkflow"

    def test_register_activity_with_inline_compensation_config(self):
        """Test registering an activity with inline CompensationConfig."""

        @ActionsHub.register_activity(
            "Test activity with inline config",
            compensation=CompensationConfig(
                action_type=CompensationActionType.ACTIVITY,
                action_name="inline_rollback",
            ),
        )
        def test_activity_inline(param1: str) -> str:
            return f"Hello {param1}"

        activity = ActionsHub.get_activity_by_name("test_activity_inline")
        assert activity is not None
        assert activity.compensation_config is not None
        assert activity.compensation_config.action_name == "inline_rollback"

    def test_get_compensation_config_existing_activity(self):
        """Test get_compensation_config() for an existing activity with compensation."""
        compensation = activity_compensation("cleanup_action")

        @ActionsHub.register_activity(
            "Test activity",
            compensation=compensation,
        )
        def test_get_comp_activity(param1: str) -> str:
            return param1

        config = ActionsHub.get_compensation_config("test_get_comp_activity")
        assert config is not None
        assert config.action_type == CompensationActionType.ACTIVITY
        assert config.action_name == "cleanup_action"

    def test_get_compensation_config_activity_without_compensation(self):
        """Test get_compensation_config() for an activity without compensation."""

        @ActionsHub.register_activity("Test activity without comp")
        def test_no_comp_activity(param1: str) -> str:
            return param1

        config = ActionsHub.get_compensation_config("test_no_comp_activity")
        assert config is None

    def test_get_compensation_config_non_existent_activity(self):
        """Test get_compensation_config() for a non-existent activity."""
        config = ActionsHub.get_compensation_config("non_existent_activity")
        assert config is None

    def test_has_compensation_true(self):
        """Test has_compensation() returns True for activity with compensation."""
        compensation = activity_compensation("delete_action")

        @ActionsHub.register_activity(
            "Test activity",
            compensation=compensation,
        )
        def test_has_comp_true(param1: str) -> str:
            return param1

        assert ActionsHub.has_compensation("test_has_comp_true") is True

    def test_has_compensation_false_no_compensation(self):
        """Test has_compensation() returns False for activity without compensation."""

        @ActionsHub.register_activity("Test activity")
        def test_has_comp_false(param1: str) -> str:
            return param1

        assert ActionsHub.has_compensation("test_has_comp_false") is False

    def test_has_compensation_false_non_existent(self):
        """Test has_compensation() returns False for non-existent activity."""
        assert ActionsHub.has_compensation("non_existent_activity") is False

    def test_register_activity_preserves_other_metadata(self):
        """Test that registering with compensation preserves other activity metadata."""
        from zamp_public_workflow_sdk.actions_hub.models.mcp_models import MCPConfig

        mcp_config = MCPConfig(service_name="test_service", accesses=[])
        compensation = activity_compensation("rollback")

        @ActionsHub.register_activity(
            "Test activity with all metadata",
            labels=["test", "saga"],
            mcp_config=mcp_config,
            compensation=compensation,
        )
        def test_all_metadata(param1: str) -> str:
            return param1

        activity = ActionsHub.get_activity_by_name("test_all_metadata")
        assert activity is not None
        assert activity.description == "Test activity with all metadata"
        assert activity.mcp_config is not None
        assert activity.mcp_config.service_name == "test_service"
        assert activity.compensation_config is not None
        assert activity.compensation_config.action_name == "rollback"


class TestCompensationConfigIntegration:
    """Integration tests for compensation configuration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.original_activities = ActionsHub._activities.copy()
        ActionsHub._activities.clear()

    def teardown_method(self):
        """Restore original registries after each test."""
        ActionsHub._activities.clear()
        ActionsHub._activities.update(self.original_activities)

    def test_full_saga_registration_pattern(self):
        """Test the full pattern of registering main activity and compensation activity."""

        # Step 1: Register the compensation activity first
        @ActionsHub.register_activity("Delete Slack message compensation")
        def delete_slack_message(channel: str, message_ts: str, result: dict) -> bool:
            # This would delete the message in real implementation
            return True

        # Step 2: Register the main activity with compensation reference
        @ActionsHub.register_activity(
            "Send Slack message",
            compensation=activity_compensation("delete_slack_message"),
        )
        def send_slack_message(channel: str, text: str) -> dict:
            return {"ts": "1234567890.123456", "channel": channel}

        # Verify both activities are registered
        assert ActionsHub.get_activity_by_name("delete_slack_message") is not None
        assert ActionsHub.get_activity_by_name("send_slack_message") is not None

        # Verify compensation is linked
        config = ActionsHub.get_compensation_config("send_slack_message")
        assert config is not None
        assert config.action_name == "delete_slack_message"
        assert config.action_type == CompensationActionType.ACTIVITY

        # Verify compensation activity exists
        compensation_activity = ActionsHub.get_activity_by_name(config.action_name)
        assert compensation_activity is not None

    def test_multiple_activities_with_compensation(self):
        """Test registering multiple activities with different compensations."""

        # Register compensation activities
        @ActionsHub.register_activity("Rollback A")
        def rollback_a(data: str) -> bool:
            return True

        @ActionsHub.register_activity("Rollback B")
        def rollback_b(data: str) -> bool:
            return True

        # Register main activities with their compensations
        @ActionsHub.register_activity(
            "Action A",
            compensation=activity_compensation("rollback_a"),
        )
        def action_a(data: str) -> str:
            return data

        @ActionsHub.register_activity(
            "Action B",
            compensation=activity_compensation("rollback_b"),
        )
        def action_b(data: str) -> str:
            return data

        @ActionsHub.register_activity("Action C (no compensation)")
        def action_c(data: str) -> str:
            return data

        # Verify compensations are correctly linked
        assert ActionsHub.has_compensation("action_a") is True
        assert ActionsHub.has_compensation("action_b") is True
        assert ActionsHub.has_compensation("action_c") is False

        assert ActionsHub.get_compensation_config("action_a").action_name == "rollback_a"
        assert ActionsHub.get_compensation_config("action_b").action_name == "rollback_b"
        assert ActionsHub.get_compensation_config("action_c") is None
