"""
Unit tests for simulation activities.
"""

import base64
from unittest.mock import AsyncMock, patch

import pytest

from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode
from zamp_public_workflow_sdk.simulation.activities import get_simulation_data_from_s3, return_mocked_result
from zamp_public_workflow_sdk.simulation.models import NodeMockConfig
from zamp_public_workflow_sdk.simulation.models.config import SimulationConfig
from zamp_public_workflow_sdk.simulation.models.mocked_result import MockedResultInput, MockedResultOutput
from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload
from zamp_public_workflow_sdk.simulation.models.simulation_s3 import (
    DownloadFromS3Output,
    GetSimulationDataFromS3Input,
    SimulationMemo,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import DecodeNodePayloadOutput


class TestReturnMockedResult:
    """Test cases for return_mocked_result activity."""

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_decoding_needed_raw_output(self):
        """Test return_mocked_result with raw output payload that doesn't need decoding."""
        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload={"result": "raw_value"},
            action_name="test_action",
        )

        result = await return_mocked_result(input_params)

        assert isinstance(result, MockedResultOutput)
        assert result.root == {"result": "raw_value"}

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_decoding_needed_no_encoding_metadata(self):
        """Test return_mocked_result with dict payload without encoding metadata."""
        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload={"input": "value"},
            output_payload={"output": "value"},
            action_name="test_action",
        )

        result = await return_mocked_result(input_params)

        assert isinstance(result, MockedResultOutput)
        assert result.root == {"output": "value"}

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_decoding_needed_none_payloads(self):
        """Test return_mocked_result with None payloads."""
        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload=None,
            action_name="test_action",
        )

        result = await return_mocked_result(input_params)

        assert isinstance(result, MockedResultOutput)
        assert result.root is None

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_decoding_needed_non_dict_payload(self):
        """Test return_mocked_result with non-dict payload (string, list, etc.)."""
        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload="string_input",
            output_payload=[1, 2, 3],
            action_name="test_action",
        )

        result = await return_mocked_result(input_params)

        assert isinstance(result, MockedResultOutput)
        assert result.root == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_return_mocked_result_output_needs_decoding(self):
        """Test return_mocked_result when output payload needs decoding."""
        encoded_output = {
            "metadata": {"encoding": "json/plain"},
            "data": "encoded_data",
        }

        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload=encoded_output,
            action_name="test_action",
        )

        decoded_result = "decoded_value"

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = DecodeNodePayloadOutput(
                decoded_input=None,
                decoded_output=decoded_result,
            )

            result = await return_mocked_result(input_params)

            assert isinstance(result, MockedResultOutput)
            assert result.root == decoded_result
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
        encoded_output = {
            "metadata": {"encoding": "json/plain"},
            "data": "encoded_output_data",
        }

        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=encoded_input,
            output_payload=encoded_output,
            action_name="test_action",
        )

        decoded_result = "decoded_value"

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = DecodeNodePayloadOutput(
                decoded_input="decoded_input_value",
                decoded_output=decoded_result,
            )

            result = await return_mocked_result(input_params)

            assert isinstance(result, MockedResultOutput)
            assert result.root == decoded_result
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

        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=encoded_input,
            output_payload=encoded_output,
            action_name="test_action",
        )

        decoded_result = "decoded_value"

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = DecodeNodePayloadOutput(
                decoded_input="decoded_input_value",
                decoded_output=decoded_result,
            )

            result = await return_mocked_result(input_params)

            assert isinstance(result, MockedResultOutput)
            assert result.root == decoded_result
            mock_execute.assert_called_once()
            assert mock_execute.call_args[1]["execution_mode"] == ExecutionMode.API

    @pytest.mark.asyncio
    async def test_return_mocked_result_decoding_failure(self):
        """Test return_mocked_result when decoding fails."""
        encoded_output = {
            "metadata": {"encoding": "json/plain"},
            "data": "encoded_data",
        }

        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload=encoded_output,
            action_name="test_action",
        )

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = Exception("Decoding failed")

            with pytest.raises(Exception, match="Decoding failed"):
                await return_mocked_result(input_params)

            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_return_mocked_result_encoding_metadata_missing(self):
        """Test return_mocked_result when dict has metadata but no encoding field."""
        payload_with_metadata_no_encoding = {
            "metadata": {"some_other_field": "value"},
            "data": "some_data",
        }

        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload=payload_with_metadata_no_encoding,
            action_name="test_action",
        )

        result = await return_mocked_result(input_params)

        # Should return raw output since encoding is None
        assert isinstance(result, MockedResultOutput)
        assert result.root == payload_with_metadata_no_encoding

    @pytest.mark.asyncio
    async def test_return_mocked_result_encoding_metadata_none(self):
        """Test return_mocked_result when encoding field is explicitly None."""
        payload_with_none_encoding = {
            "metadata": {"encoding": None},
            "data": "some_data",
        }

        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload=payload_with_none_encoding,
            action_name="test_action",
        )

        result = await return_mocked_result(input_params)

        # Should return raw output since encoding is None
        assert isinstance(result, MockedResultOutput)
        assert result.root == payload_with_none_encoding

    @pytest.mark.asyncio
    async def test_return_mocked_result_empty_metadata_dict(self):
        """Test return_mocked_result when metadata is empty dict."""
        payload_with_empty_metadata = {
            "metadata": {},
            "data": "some_data",
        }

        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload=payload_with_empty_metadata,
            action_name="test_action",
        )

        result = await return_mocked_result(input_params)

        # Should return raw output since encoding is None
        assert isinstance(result, MockedResultOutput)
        assert result.root == payload_with_empty_metadata

    @pytest.mark.asyncio
    async def test_return_mocked_result_no_metadata_key(self):
        """Test return_mocked_result when dict has no metadata key."""
        payload_no_metadata = {
            "data": "some_data",
        }

        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload=payload_no_metadata,
            action_name="test_action",
        )

        result = await return_mocked_result(input_params)

        # Should return raw output since no metadata
        assert isinstance(result, MockedResultOutput)
        assert result.root == payload_no_metadata

    @pytest.mark.asyncio
    async def test_return_mocked_result_with_action_name(self):
        """Test return_mocked_result with action_name provided."""
        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload={"result": "value"},
            action_name="my_test_action",
        )

        result = await return_mocked_result(input_params)

        assert isinstance(result, MockedResultOutput)
        assert result.root == {"result": "value"}

    @pytest.mark.asyncio
    async def test_return_mocked_result_without_action_name(self):
        """Test return_mocked_result without action_name."""
        input_params = MockedResultInput(
            node_id="test_node#1",
            input_payload=None,
            output_payload={"result": "value"},
        )

        result = await return_mocked_result(input_params)

        assert isinstance(result, MockedResultOutput)
        assert result.root == {"result": "value"}


class TestGetSimulationDataFromS3:
    """Test cases for get_simulation_data_from_s3 activity."""

    @pytest.mark.asyncio
    async def test_get_simulation_data_from_s3_success(self):
        """Test successful download and decoding of simulation data from S3."""
        # Create mock simulation data
        mock_config = SimulationConfig(mock_config=NodeMockConfig(node_strategies=[]))
        mock_node_payload = NodePayload(node_id="test#1", input_payload="test_input", output_payload="test_output")
        simulation_memo = SimulationMemo(
            config=mock_config,
            node_id_to_payload_map={"test#1": mock_node_payload},
        )

        # Encode the data as it would be stored in S3
        content_base64 = base64.b64encode(simulation_memo.model_dump_json().encode()).decode()
        mock_download_result = DownloadFromS3Output(content_base64=content_base64)

        input_params = GetSimulationDataFromS3Input(
            simulation_s3_key="simulation-data/test_wf.json",
            bucket_name="test-bucket",
        )

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = mock_download_result

            result = await get_simulation_data_from_s3(input_params)

            assert result is not None
            assert hasattr(result, "simulation_memo")
            assert result.simulation_memo.config is not None
            assert "test#1" in result.simulation_memo.node_id_to_payload_map

            # Verify execute_activity was called correctly
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][0] == "download_from_s3"
            assert call_args[1]["skip_simulation"] is True
            assert call_args[1]["return_type"] == DownloadFromS3Output

    @pytest.mark.asyncio
    async def test_get_simulation_data_from_s3_download_failure(self):
        """Test handling of download failure from S3."""
        input_params = GetSimulationDataFromS3Input(
            simulation_s3_key="simulation-data/test_wf.json",
            bucket_name="test-bucket",
        )

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.side_effect = Exception("S3 download failed")

            with pytest.raises(Exception, match="Failed to get simulation data from S3: S3 download failed"):
                await get_simulation_data_from_s3(input_params)

            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_simulation_data_from_s3_decode_failure(self):
        """Test handling of decode failure."""
        # Create invalid base64 content
        invalid_content_base64 = "invalid_base64_content"
        mock_download_result = DownloadFromS3Output(content_base64=invalid_content_base64)

        input_params = GetSimulationDataFromS3Input(
            simulation_s3_key="simulation-data/test_wf.json",
            bucket_name="test-bucket",
        )

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = mock_download_result

            with pytest.raises(Exception, match="Failed to get simulation data from S3"):
                await get_simulation_data_from_s3(input_params)

            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_simulation_data_from_s3_invalid_json(self):
        """Test handling of invalid JSON data."""
        # Create invalid JSON content
        invalid_json = base64.b64encode(b"invalid json {]").decode()
        mock_download_result = DownloadFromS3Output(content_base64=invalid_json)

        input_params = GetSimulationDataFromS3Input(
            simulation_s3_key="simulation-data/test_wf.json",
            bucket_name="test-bucket",
        )

        with patch(
            "zamp_public_workflow_sdk.simulation.activities.ActionsHub.execute_activity",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = mock_download_result

            with pytest.raises(Exception, match="Failed to get simulation data from S3"):
                await get_simulation_data_from_s3(input_params)

            mock_execute.assert_called_once()
