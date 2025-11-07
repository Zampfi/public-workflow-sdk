import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_workflow_history():
    """Create a mock WorkflowHistory object."""
    history = MagicMock()
    history.workflow_id = "test-workflow-id"
    history.run_id = "test-run-id"
    history.events = []
    return history


@pytest.fixture
def mock_encoded_payload():
    """Create a mock encoded NodePayload."""
    payload = MagicMock()
    payload.node_id = "test_node#1"
    payload.input_payload = "encoded_input_data"
    payload.output_payload = "encoded_output_data"
    return payload


@pytest.fixture
def mock_decoded_output():
    """Create a mock DecodeNodePayloadOutput."""
    output = MagicMock()
    output.decoded_input = {"test": "input"}
    output.decoded_output = {"test": "output"}
    return output


class TestBuildNodePayload:
    """Tests for build_node_payload function."""

    @pytest.mark.asyncio
    async def test_build_node_payload_success(self, mock_workflow_history, mock_encoded_payload, mock_decoded_output):
        """Test successful building of node payload results."""
        from zamp_public_workflow_sdk.simulation.helper import build_node_payload
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        output_config = {
            "node1#1": NodePayloadType.INPUT_OUTPUT,
            "node2#1": NodePayloadType.OUTPUT,
        }

        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_temporal_history",
            return_value=mock_workflow_history,
        ) as mock_fetch:
            with patch(
                "zamp_public_workflow_sdk.simulation.helper.extract_node_payload",
                return_value={
                    "node1#1": mock_encoded_payload,
                    "node2#1": mock_encoded_payload,
                },
            ) as mock_extract:
                with patch(
                    "zamp_public_workflow_sdk.simulation.helper._decode_node_payload",
                    return_value=mock_decoded_output,
                ) as mock_decode:
                    result = await build_node_payload(
                        workflow_id="wf-123",
                        run_id="run-456",
                        output_config=output_config,
                    )

                    # Verify calls
                    mock_fetch.assert_called_once_with(
                        node_ids=["node1#1", "node2#1"],
                        workflow_id="wf-123",
                        run_id="run-456",
                    )
                    mock_extract.assert_called_once()
                    assert mock_decode.call_count == 2

                    # Verify results
                    assert len(result) == 2
                    assert result[0].node_id == "node1#1"
                    assert result[1].node_id == "node2#1"

    @pytest.mark.asyncio
    async def test_build_node_payload_no_history(self):
        """Test when temporal history fetch fails."""
        from zamp_public_workflow_sdk.simulation.helper import build_node_payload
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        output_config = {"node1#1": NodePayloadType.INPUT}

        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_temporal_history",
            return_value=None,
        ):
            with pytest.raises(Exception, match="Failed to fetch temporal history"):
                await build_node_payload(
                    workflow_id="wf-123",
                    run_id="run-456",
                    output_config=output_config,
                )

    @pytest.mark.asyncio
    async def test_build_node_payload_empty_config(self, mock_workflow_history):
        """Test with empty output config."""
        from zamp_public_workflow_sdk.simulation.helper import build_node_payload

        output_config = {}

        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_temporal_history",
            return_value=mock_workflow_history,
        ):
            with patch(
                "zamp_public_workflow_sdk.simulation.helper.extract_node_payload",
                return_value={},
            ):
                result = await build_node_payload(
                    workflow_id="wf-123",
                    run_id="run-456",
                    output_config=output_config,
                )

                assert result == []

    @pytest.mark.asyncio
    async def test_build_node_payload_partial_failures(
        self, mock_workflow_history, mock_encoded_payload, mock_decoded_output
    ):
        """Test when some nodes fail to decode."""
        from zamp_public_workflow_sdk.simulation.helper import build_node_payload
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        output_config = {
            "node1#1": NodePayloadType.INPUT,
            "node2#1": NodePayloadType.OUTPUT,
            "node3#1": NodePayloadType.INPUT_OUTPUT,
        }

        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_temporal_history",
            return_value=mock_workflow_history,
        ):
            with patch(
                "zamp_public_workflow_sdk.simulation.helper.extract_node_payload",
                return_value={
                    "node1#1": mock_encoded_payload,
                    "node2#1": mock_encoded_payload,
                    "node3#1": None,  # Missing payload
                },
            ):
                with patch(
                    "zamp_public_workflow_sdk.simulation.helper._decode_node_payload",
                    side_effect=[mock_decoded_output, None],  # Second decode fails
                ):
                    result = await build_node_payload(
                        workflow_id="wf-123",
                        run_id="run-456",
                        output_config=output_config,
                    )

                    # Only node1#1 succeeds
                    assert len(result) == 1
                    assert result[0].node_id == "node1#1"


class TestDecodeAndBuildResults:
    """Tests for _decode_and_build_results function."""

    @pytest.mark.asyncio
    async def test_decode_and_build_results_success(self, mock_encoded_payload, mock_decoded_output):
        """Test successful decoding and building of results."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_and_build_results
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType, NodePayloadResult

        encoded_payloads = {
            "node1#1": mock_encoded_payload,
            "node2#1": mock_encoded_payload,
        }
        output_config = {
            "node1#1": NodePayloadType.INPUT,
            "node2#1": NodePayloadType.OUTPUT,
        }

        with patch(
            "zamp_public_workflow_sdk.simulation.helper._decode_node_payload",
            return_value=mock_decoded_output,
        ) as mock_decode:
            result = await _decode_and_build_results(
                encoded_node_payloads=encoded_payloads,
                output_config=output_config,
                workflow_id="wf-123",
            )

            assert len(result) == 2
            assert mock_decode.call_count == 2
            assert all(isinstance(r, NodePayloadResult) for r in result)

    @pytest.mark.asyncio
    async def test_decode_and_build_results_input_only(self, mock_encoded_payload):
        """Test building results with INPUT payload type only."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_and_build_results
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        mock_decoded = MagicMock()
        mock_decoded.decoded_input = {"test": "input"}
        mock_decoded.decoded_output = None

        encoded_payloads = {"node1#1": mock_encoded_payload}
        output_config = {"node1#1": NodePayloadType.INPUT}

        with patch(
            "zamp_public_workflow_sdk.simulation.helper._decode_node_payload",
            return_value=mock_decoded,
        ):
            result = await _decode_and_build_results(
                encoded_node_payloads=encoded_payloads,
                output_config=output_config,
                workflow_id="wf-123",
            )

            assert len(result) == 1
            assert result[0].node_id == "node1#1"
            assert result[0].input == {"test": "input"}
            assert result[0].output is None

    @pytest.mark.asyncio
    async def test_decode_and_build_results_output_only(self, mock_encoded_payload):
        """Test building results with OUTPUT payload type only."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_and_build_results
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        mock_decoded = MagicMock()
        mock_decoded.decoded_input = None
        mock_decoded.decoded_output = {"test": "output"}

        encoded_payloads = {"node1#1": mock_encoded_payload}
        output_config = {"node1#1": NodePayloadType.OUTPUT}

        with patch(
            "zamp_public_workflow_sdk.simulation.helper._decode_node_payload",
            return_value=mock_decoded,
        ):
            result = await _decode_and_build_results(
                encoded_node_payloads=encoded_payloads,
                output_config=output_config,
                workflow_id="wf-123",
            )

            assert len(result) == 1
            assert result[0].node_id == "node1#1"
            assert result[0].input is None
            assert result[0].output == {"test": "output"}

    @pytest.mark.asyncio
    async def test_decode_and_build_results_input_output(self, mock_encoded_payload, mock_decoded_output):
        """Test building results with INPUT_OUTPUT payload type."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_and_build_results
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        encoded_payloads = {"node1#1": mock_encoded_payload}
        output_config = {"node1#1": NodePayloadType.INPUT_OUTPUT}

        with patch(
            "zamp_public_workflow_sdk.simulation.helper._decode_node_payload",
            return_value=mock_decoded_output,
        ):
            result = await _decode_and_build_results(
                encoded_node_payloads=encoded_payloads,
                output_config=output_config,
                workflow_id="wf-123",
            )

            assert len(result) == 1
            assert result[0].node_id == "node1#1"
            assert result[0].input == {"test": "input"}
            assert result[0].output == {"test": "output"}

    @pytest.mark.asyncio
    async def test_decode_and_build_results_missing_payload(
        self,
    ):
        """Test when encoded payload is missing for a node."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_and_build_results
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        encoded_payloads = {}  # Empty - node1#1 is missing
        output_config = {"node1#1": NodePayloadType.INPUT}

        result = await _decode_and_build_results(
            encoded_node_payloads=encoded_payloads,
            output_config=output_config,
            workflow_id="wf-123",
        )

        # Should skip missing nodes
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_decode_and_build_results_decode_failure(self, mock_encoded_payload):
        """Test when decoding fails for a node."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_and_build_results
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        encoded_payloads = {"node1#1": mock_encoded_payload}
        output_config = {"node1#1": NodePayloadType.INPUT}

        with patch(
            "zamp_public_workflow_sdk.simulation.helper._decode_node_payload",
            return_value=None,  # Decode fails
        ):
            result = await _decode_and_build_results(
                encoded_node_payloads=encoded_payloads,
                output_config=output_config,
                workflow_id="wf-123",
            )

            # Should skip failed decodes
            assert len(result) == 0


class TestDecodeNodePayload:
    """Tests for _decode_node_payload function."""

    @pytest.mark.asyncio
    async def test_decode_node_payload_input(self, mock_encoded_payload):
        """Test decoding INPUT payload."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_node_payload
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType
        from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import DecodeNodePayloadInput

        mock_output = MagicMock()
        mock_output.decoded_input = {"test": "input"}
        mock_output.decoded_output = None

        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_activity",
            return_value=mock_output,
        ) as mock_execute:
            result = await _decode_node_payload(
                node_id="node1#1",
                encoded_payload=mock_encoded_payload,
                payload_type=NodePayloadType.INPUT,
            )

            assert result == mock_output
            mock_execute.assert_called_once()

            # Verify the decode input
            call_args = mock_execute.call_args[0][1]
            assert isinstance(call_args, DecodeNodePayloadInput)
            assert call_args.node_id == "node1#1"
            assert call_args.input_payload == "encoded_input_data"
            assert call_args.output_payload is None

    @pytest.mark.asyncio
    async def test_decode_node_payload_output(self, mock_encoded_payload):
        """Test decoding OUTPUT payload."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_node_payload
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        mock_output = MagicMock()
        mock_output.decoded_input = None
        mock_output.decoded_output = {"test": "output"}

        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_activity",
            return_value=mock_output,
        ) as mock_execute:
            result = await _decode_node_payload(
                node_id="node1#1",
                encoded_payload=mock_encoded_payload,
                payload_type=NodePayloadType.OUTPUT,
            )

            assert result == mock_output

            # Verify the decode input
            call_args = mock_execute.call_args[0][1]
            assert call_args.input_payload is None
            assert call_args.output_payload == "encoded_output_data"

    @pytest.mark.asyncio
    async def test_decode_node_payload_input_output(self, mock_encoded_payload):
        """Test decoding INPUT_OUTPUT payload."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_node_payload
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        mock_output = MagicMock()
        mock_output.decoded_input = {"test": "input"}
        mock_output.decoded_output = {"test": "output"}

        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_activity",
            return_value=mock_output,
        ) as mock_execute:
            result = await _decode_node_payload(
                node_id="node1#1",
                encoded_payload=mock_encoded_payload,
                payload_type=NodePayloadType.INPUT_OUTPUT,
            )

            assert result == mock_output

            # Verify both payloads are included
            call_args = mock_execute.call_args[0][1]
            assert call_args.input_payload == "encoded_input_data"
            assert call_args.output_payload == "encoded_output_data"

    @pytest.mark.asyncio
    async def test_decode_node_payload_failure(self, mock_encoded_payload):
        """Test decoding failure."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_node_payload
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType

        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_activity",
            side_effect=Exception("Decode failed"),
        ):
            result = await _decode_node_payload(
                node_id="node1#1",
                encoded_payload=mock_encoded_payload,
                payload_type=NodePayloadType.INPUT,
            )

            # Should return None on failure
            assert result is None

    @pytest.mark.asyncio
    async def test_decode_node_payload_activity_call(self, mock_encoded_payload):
        """Test that decode_node_payload activity is called correctly."""
        from zamp_public_workflow_sdk.simulation.helper import _decode_node_payload
        from zamp_public_workflow_sdk.simulation.models.simulation_workflow import NodePayloadType
        from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import DecodeNodePayloadOutput

        mock_output = MagicMock()
        mock_output.decoded_input = {"test": "data"}
        mock_output.decoded_output = None

        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_activity",
            return_value=mock_output,
        ) as mock_execute:
            await _decode_node_payload(
                node_id="test_node#1",
                encoded_payload=mock_encoded_payload,
                payload_type=NodePayloadType.INPUT,
            )

            # Verify activity name
            assert mock_execute.call_args[0][0] == "decode_node_payload"

            # Verify summary
            assert "test_node#1" in str(mock_execute.call_args[1].get("summary", ""))

            # Verify return type
            assert mock_execute.call_args[1]["return_type"] == DecodeNodePayloadOutput
