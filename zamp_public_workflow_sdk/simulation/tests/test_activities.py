"""
Unit tests for simulation activities.
"""

from unittest.mock import patch

import pytest

from zamp_public_workflow_sdk.simulation.activities import return_mocked_result


class TestReturnMockedResult:
    """Test return_mocked_result activity."""

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_string(self):
        """Test return_mocked_result with string output."""
        node_id = "TestActivity#1"
        label = "response mocked TestActivity#1"
        output = "test_output"

        result = await return_mocked_result(node_id, label, output)

        assert result == "test_output"

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_dict(self):
        """Test return_mocked_result with dict output."""
        node_id = "TestActivity#1"
        label = "response mocked TestActivity#1"
        output = {"key": "value", "number": 123}

        result = await return_mocked_result(node_id, label, output)

        assert result == {"key": "value", "number": 123}
        assert result["key"] == "value"
        assert result["number"] == 123

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_list(self):
        """Test return_mocked_result with list output."""
        node_id = "TestActivity#1"
        label = "response mocked TestActivity#1"
        output = [1, 2, 3, "test"]

        result = await return_mocked_result(node_id, label, output)

        assert result == [1, 2, 3, "test"]
        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_none(self):
        """Test return_mocked_result with None output."""
        node_id = "TestActivity#1"
        label = "response mocked TestActivity#1"
        output = None

        result = await return_mocked_result(node_id, label, output)

        assert result is None

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_nested_structure(self):
        """Test return_mocked_result with nested dict/list structure."""
        node_id = "TestWorkflow#1"
        label = "response mocked TestWorkflow#1"
        output = {
            "data": [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}],
            "metadata": {"count": 2, "timestamp": "2024-01-01"},
        }

        result = await return_mocked_result(node_id, label, output)

        assert result == output
        assert result["data"][0]["id"] == 1
        assert result["metadata"]["count"] == 2

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_hierarchical_node_id(self):
        """Test return_mocked_result with hierarchical node_id."""
        node_id = "ParentWorkflow#1.ChildActivity#2"
        label = "response mocked ParentWorkflow#1.ChildActivity#2"
        output = "nested_result"

        result = await return_mocked_result(node_id, label, output)

        assert result == "nested_result"

    @pytest.mark.asyncio
    async def test_return_mocked_result_logging(self):
        """Test return_mocked_result logs the correct information."""
        node_id = "TestActivity#1"
        label = "response mocked TestActivity#1"
        output = "test_output"

        with patch("zamp_public_workflow_sdk.simulation.activities.logger") as mock_logger:
            result = await return_mocked_result(node_id, label, output)

            assert result == "test_output"
            mock_logger.info.assert_called_once_with(
                "Returning mocked result", label="response mocked TestActivity#1", node_id="TestActivity#1"
            )

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_empty_node_id(self):
        """Test return_mocked_result with empty node_id string."""
        node_id = ""
        label = "response mocked "
        output = "test_output"

        result = await return_mocked_result(node_id, label, output)

        assert result == "test_output"

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_complex_label(self):
        """Test return_mocked_result with complex label containing special characters."""
        node_id = "TestActivity#1"
        label = "Test_Activity-With.Special:Characters"
        output = "test_output"

        result = await return_mocked_result(node_id, label, output)

        assert result == "test_output"

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_boolean(self):
        """Test return_mocked_result with boolean output."""
        node_id = "TestActivity#1"
        label = "response mocked TestActivity#1"
        output = True

        result = await return_mocked_result(node_id, label, output)

        assert result is True

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_numeric_types(self):
        """Test return_mocked_result with various numeric types."""
        node_id = "TestActivity#1"
        label = "response mocked TestActivity#1"

        # Test integer
        result_int = await return_mocked_result(node_id, label, 42)
        assert result_int == 42

        # Test float
        result_float = await return_mocked_result(node_id, label, 3.14)
        assert result_float == 3.14

        # Test negative number
        result_negative = await return_mocked_result(node_id, label, -100)
        assert result_negative == -100
