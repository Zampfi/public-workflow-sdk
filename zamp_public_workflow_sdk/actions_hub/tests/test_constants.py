"""
Tests for constants.py
"""

import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from zamp_public_workflow_sdk.actions_hub.constants import DEFAULT_MODE, ExecutionMode


class TestConstants:
    """Test the constants module."""

    def test_default_mode(self):
        """Test DEFAULT_MODE constant."""
        assert DEFAULT_MODE == "default"

    def test_execution_mode_enum(self):
        """Test ExecutionMode enum values."""
        assert ExecutionMode.API == "API"
        assert ExecutionMode.TEMPORAL == "TEMPORAL"

    def test_execution_mode_enum_membership(self):
        """Test ExecutionMode enum membership."""
        assert ExecutionMode.API in ExecutionMode
        assert ExecutionMode.TEMPORAL in ExecutionMode

    def test_execution_mode_string_representation(self):
        """Test ExecutionMode string representation."""
        assert str(ExecutionMode.API) == "ExecutionMode.API"
        assert str(ExecutionMode.TEMPORAL) == "ExecutionMode.TEMPORAL"

    def test_execution_mode_equality(self):
        """Test ExecutionMode equality comparisons."""
        assert ExecutionMode.API == ExecutionMode.API
        assert ExecutionMode.TEMPORAL == ExecutionMode.TEMPORAL
        assert ExecutionMode.API != ExecutionMode.TEMPORAL
