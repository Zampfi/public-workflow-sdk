"""
Unit tests for simulation activities.
"""

from unittest.mock import AsyncMock, patch

import pytest

from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode
from zamp_public_workflow_sdk.simulation.constants import PayloadKey
from zamp_public_workflow_sdk.simulation.models.mocked_result import MockedResultInput, MockedResultOutput
from zamp_public_workflow_sdk.simulation.activities import return_mocked_result


class TestReturnMockedResult:
    """Test cases for return_mocked_result activity."""

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_decoding_needed_raw_output(self):
        """Test return_mocked_result with raw output payload that doesn't need decoding."""
        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: {"result": "raw_value"},
            },
            action_name="test_action",
        )

        result = await return_mocked_result(input_data)

        assert isinstance(result, MockedResultOutput)
        assert result.output == {"result": "raw_value"}

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_decoding_needed_no_encoding_metadata(self):
        """Test return_mocked_result with dict payload without encoding metadata."""
        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: {"input": "value"},
                PayloadKey.OUTPUT_PAYLOAD: {"output": "value"},
            },
            action_name="test_action",
        )

        result = await return_mocked_result(input_data)

        assert isinstance(result, MockedResultOutput)
        assert result.output == {"output": "value"}

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_decoding_needed_none_payloads(self):
        """Test return_mocked_result with None payloads."""
        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: None,
            },
            action_name="test_action",
        )

        result = await return_mocked_result(input_data)

        assert isinstance(result, MockedResultOutput)
        assert result.output is None

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_decoding_needed_non_dict_payload(self):
        """Test return_mocked_result with non-dict payload (string, list, etc.)."""
        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: "string_input",
                PayloadKey.OUTPUT_PAYLOAD: [1, 2, 3],
            },
            action_name="test_action",
        )

        result = await return_mocked_result(input_data)

        assert isinstance(result, MockedResultOutput)
        assert result.output == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_return_mocked_result_output_needs_decoding(self):
        """Test return_mocked_result when output payload needs decoding."""
        encoded_output = {
            "metadata": {"encoding": "json/plain"},
            "data": "encoded_data",
        }

        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: encoded_output,
            },
            action_name="test_action",
        )

        decoded_result = {"result": "decoded_value"}

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = decoded_result

            result = await return_mocked_result(input_data)

            assert isinstance(result, MockedResultOutput)
            assert result.output == decoded_result
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][0] == "decode_node_payload"
            assert call_args[1]["execution_mode"] == ExecutionMode.API
            assert call_args[0][1].node_id == "test_node#1"

    @pytest.mark.asyncio
    async def test_return_mocked_result_input_needs_decoding(self):
        """Test return_mocked_result when input payload needs decoding."""
        encoded_input = {
            "metadata": {"encoding": "json/plain"},
            "data": "encoded_input_data",
        }

        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: encoded_input,
                PayloadKey.OUTPUT_PAYLOAD: {"result": "raw_output"},
            },
            action_name="test_action",
        )

        decoded_result = {"result": "decoded_value"}

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = decoded_result

            result = await return_mocked_result(input_data)

            assert isinstance(result, MockedResultOutput)
            assert result.output == decoded_result
            mock_execute.assert_called_once()
            assert mock_execute.call_args[1]["execution_mode"] == ExecutionMode.API

    @pytest.mark.asyncio
    async def test_return_mocked_result_both_needs_decoding(self):
        """Test return_mocked_result when both input and output payloads need decoding."""
        encoded_input = {
            "metadata": {"encoding": "json/plain"},
            "data": "encoded_input_data",
        }
        encoded_output = {
            "metadata": {"encoding": "json/plain"},
            "data": "encoded_output_data",
        }

        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: encoded_input,
                PayloadKey.OUTPUT_PAYLOAD: encoded_output,
            },
            action_name="test_action",
        )

        decoded_result = {"result": "decoded_value"}

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = decoded_result

            result = await return_mocked_result(input_data)

            assert isinstance(result, MockedResultOutput)
            assert result.output == decoded_result
            mock_execute.assert_called_once()
            assert mock_execute.call_args[1]["execution_mode"] == ExecutionMode.API

    @pytest.mark.asyncio
    async def test_return_mocked_result_decoding_failure(self):
        """Test return_mocked_result when decoding fails."""
        encoded_output = {
            "metadata": {"encoding": "json/plain"},
            "data": "encoded_data",
        }

        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: encoded_output,
            },
            action_name="test_action",
        )

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = Exception("Decoding failed")

            with pytest.raises(Exception, match="Decoding failed"):
                await return_mocked_result(input_data)

            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_return_mocked_result_encoding_metadata_missing(self):
        """Test return_mocked_result when dict has metadata but no encoding field."""
        payload_with_metadata_no_encoding = {
            "metadata": {"some_other_field": "value"},
            "data": "some_data",
        }

        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: payload_with_metadata_no_encoding,
            },
            action_name="test_action",
        )

        result = await return_mocked_result(input_data)

        # Should return raw output since encoding is None
        assert isinstance(result, MockedResultOutput)
        assert result.output == payload_with_metadata_no_encoding

    @pytest.mark.asyncio
    async def test_return_mocked_result_encoding_metadata_none(self):
        """Test return_mocked_result when encoding field is explicitly None."""
        payload_with_none_encoding = {
            "metadata": {"encoding": None},
            "data": "some_data",
        }

        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: payload_with_none_encoding,
            },
            action_name="test_action",
        )

        result = await return_mocked_result(input_data)

        # Should return raw output since encoding is None
        assert isinstance(result, MockedResultOutput)
        assert result.output == payload_with_none_encoding

    @pytest.mark.asyncio
    async def test_return_mocked_result_empty_metadata_dict(self):
        """Test return_mocked_result when metadata is empty dict."""
        payload_with_empty_metadata = {
            "metadata": {},
            "data": "some_data",
        }

        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: payload_with_empty_metadata,
            },
            action_name="test_action",
        )

        result = await return_mocked_result(input_data)

        # Should return raw output since encoding is None
        assert isinstance(result, MockedResultOutput)
        assert result.output == payload_with_empty_metadata

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_metadata_key(self):
        """Test return_mocked_result when dict has no metadata key."""
        payload_no_metadata = {
            "data": "some_data",
        }

        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: payload_no_metadata,
            },
            action_name="test_action",
        )

        result = await return_mocked_result(input_data)

        # Should return raw output since no metadata
        assert isinstance(result, MockedResultOutput)
        assert result.output == payload_no_metadata

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_action_name(self):
        """Test return_mocked_result with action_name provided."""
        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: {"result": "value"},
            },
            action_name="my_test_action",
        )

        result = await return_mocked_result(input_data)

        assert isinstance(result, MockedResultOutput)
        assert result.output == {"result": "value"}

    @pytest.mark.asyncio
    async def test_return_mocked_result_without_action_name(self):
        """Test return_mocked_result without action_name."""
        input_data = MockedResultInput(
            node_id="test_node#1",
            encoded_payload={
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: {"result": "value"},
            },
        )

        result = await return_mocked_result(input_data)

        assert isinstance(result, MockedResultOutput)
        assert result.output == {"result": "value"}
