"""
Tests for action_types.py
"""

from __future__ import annotations

import os
import sys

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from zamp_public_workflow_sdk.actions_hub.constants import ActionType


class TestActionType:
    """Test the ActionType enum."""

    def test_action_type_values(self):
        """Test that ActionType has the correct values."""
        assert ActionType.ACTIVITY.value == 0
        assert ActionType.WORKFLOW.value == 1
        assert ActionType.BUSINESS_LOGIC.value == 2

    def test_action_type_enum_membership(self):
        """Test ActionType enum membership."""
        assert ActionType.ACTIVITY in ActionType
        assert ActionType.WORKFLOW in ActionType
        assert ActionType.BUSINESS_LOGIC in ActionType

    def test_action_type_string_representation(self):
        """Test ActionType string representation."""
        assert str(ActionType.ACTIVITY) == "ActionType.ACTIVITY"
        assert str(ActionType.WORKFLOW) == "ActionType.WORKFLOW"
        assert str(ActionType.BUSINESS_LOGIC) == "ActionType.BUSINESS_LOGIC"

    def test_action_type_equality(self):
        """Test ActionType equality comparisons."""
        assert ActionType.ACTIVITY == ActionType.ACTIVITY
        assert ActionType.WORKFLOW == ActionType.WORKFLOW
        assert ActionType.BUSINESS_LOGIC == ActionType.BUSINESS_LOGIC

        assert ActionType.ACTIVITY != ActionType.WORKFLOW
        assert ActionType.WORKFLOW != ActionType.BUSINESS_LOGIC
        assert ActionType.ACTIVITY != ActionType.BUSINESS_LOGIC
