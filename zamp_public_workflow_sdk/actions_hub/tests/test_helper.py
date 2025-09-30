"""
Tests for helper.py
"""

import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zamp_public_workflow_sdk.actions_hub.helper import (
    remove_connection_id,
    find_connection_id_path,
    inject_connection_id,
)


class TestHelperFunctions:
    """Test the helper functions."""

    def test_remove_connection_id(self):
        """Test remove_connection_id function."""
        # Test with list containing connection identifiers
        schema = [
            {"title": "ConnectionIdentifier", "type": "object"},
            {"title": "OtherObject", "type": "object"},
            {"title": "ConnectionIdentifier", "type": "object"},
        ]

        result = remove_connection_id(schema)
        expected = [{"title": "OtherObject", "type": "object"}]
        assert result == expected

        # Test with empty list
        result = remove_connection_id([])
        assert result == []

    def test_find_connection_id_path(self):
        """Test find_connection_id_path function."""
        # Test with schema containing ConnectionIdentifier
        schema = [
            {"title": "OtherObject", "type": "object"},
            {"title": "ConnectionIdentifier", "type": "object"},
        ]

        result = find_connection_id_path(schema)
        assert result == ["1", "connection_id"]

        # Test with empty schema
        result = find_connection_id_path([])
        assert result == ["connection_id"]

    def test_inject_connection_id(self):
        """Test inject_connection_id function."""
        # Test with path starting with "0"
        params = {"param1": "value1", "param2": "value2"}
        path = ["0", "connection_id"]
        result = inject_connection_id(params, "new_conn_456", path)

        expected = [{"connection_id": "new_conn_456"}, params]
        assert result == expected

        # Test with different path
        path = ["1", "connection_id"]
        result = inject_connection_id(params, "new_conn_456", path)

        # Should return list with params and connection_id
        assert len(result) == 2
        assert result[0] == params
        assert result[1]["connection_id"] == "new_conn_456"
