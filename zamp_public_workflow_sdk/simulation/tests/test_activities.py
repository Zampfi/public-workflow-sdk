"""
Unit tests for simulation activities.
"""

from unittest.mock import patch

import pytest

from zamp_public_workflow_sdk.simulation.activities import return_mocked_result, MockedResultInput


class TestReturnMockedResult:
    """Test return_mocked_result activity."""

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_string(self):
        """Test return_mocked_result with string output."""
        node_id = "TestActivity#1"
        output = "test_output"
        input_data = MockedResultInput(node_id=node_id, output=output)

        result = await return_mocked_result(input_data)

        assert result == "test_output"

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_dict(self):
        """Test return_mocked_result with dict output."""
        node_id = "TestActivity#1"
        output = {"key": "value", "number": 123}
        input_data = MockedResultInput(node_id=node_id, output=output)

        result = await return_mocked_result(input_data)

        assert result == {"key": "value", "number": 123}
        assert result["key"] == "value"
        assert result["number"] == 123

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_list(self):
        """Test return_mocked_result with list output."""
        node_id = "TestActivity#1"
        output = [1, 2, 3, "test"]
        input_data = MockedResultInput(node_id=node_id, output=output)

        result = await return_mocked_result(input_data)

        assert result == [1, 2, 3, "test"]
        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_none(self):
        """Test return_mocked_result with None output."""
        node_id = "TestActivity#1"
        output = None
        input_data = MockedResultInput(node_id=node_id, output=output)

        result = await return_mocked_result(input_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_nested_structure(self):
        """Test return_mocked_result with nested dict/list structure."""
        node_id = "TestWorkflow#1"
        output = {
            "data": [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}],
            "metadata": {"count": 2, "timestamp": "2024-01-01"},
        }

        input_data = MockedResultInput(node_id=node_id, output=output)
        result = await return_mocked_result(input_data)

        assert result == output
        assert result["data"][0]["id"] == 1
        assert result["metadata"]["count"] == 2

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_hierarchical_node_id(self):
        """Test return_mocked_result with hierarchical node_id."""
        node_id = "ParentWorkflow#1.ChildActivity#2"
        output = "nested_result"

        input_data = MockedResultInput(node_id=node_id, output=output)
        result = await return_mocked_result(input_data)

        assert result == "nested_result"

    @pytest.mark.asyncio
    async def test_return_mocked_result_logging(self):
        """Test return_mocked_result logs the correct information."""
        node_id = "TestActivity#1"
        output = "test_output"

        with patch("zamp_public_workflow_sdk.simulation.activities.logger") as mock_logger:
            input_data = MockedResultInput(node_id=node_id, output=output)
            result = await return_mocked_result(input_data)

            assert result == "test_output"
            mock_logger.info.assert_called_once_with("Returning mocked result", node_id="TestActivity#1")

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_empty_node_id(self):
        """Test return_mocked_result with empty node_id string."""
        node_id = ""
        output = "test_output"

        input_data = MockedResultInput(node_id=node_id, output=output)
        result = await return_mocked_result(input_data)

        assert result == "test_output"

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_complex_label(self):
        """Test return_mocked_result with complex label containing special characters."""
        node_id = "TestActivity#1"
        output = "test_output"

        input_data = MockedResultInput(node_id=node_id, output=output)
        result = await return_mocked_result(input_data)

        assert result == "test_output"

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_boolean(self):
        """Test return_mocked_result with boolean output."""
        node_id = "TestActivity#1"
        output = True

        input_data = MockedResultInput(node_id=node_id, output=output)
        result = await return_mocked_result(input_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_numeric_types(self):
        """Test return_mocked_result with various numeric types."""
        node_id = "TestActivity#1"

        # Test integer
        input_data_int = MockedResultInput(node_id=node_id, output=42)
        result_int = await return_mocked_result(input_data_int)
        assert result_int == 42

        # Test float
        input_data_float = MockedResultInput(node_id=node_id, output=3.14)
        result_float = await return_mocked_result(input_data_float)
        assert result_float == 3.14

        # Test negative number
        input_data_negative = MockedResultInput(node_id=node_id, output=-100)
        result_negative = await return_mocked_result(input_data_negative)
        assert result_negative == -100
