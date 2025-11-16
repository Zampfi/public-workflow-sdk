"""
Unit tests for WorkflowSimulationService.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from zamp_public_workflow_sdk.simulation.models import (
    CustomOutputConfig,
    ExecutionType,
    NodeMockConfig,
    NodePayload,
    NodeStrategy,
    SimulationConfig,
    SimulationResponse,
    SimulationStrategyConfig,
    StrategyType,
    TemporalHistoryConfig,
)
from zamp_public_workflow_sdk.simulation.models.mocked_result import MockedResultOutput
from zamp_public_workflow_sdk.simulation.workflow_simulation_service import (
    WorkflowSimulationService,
)
from zamp_public_workflow_sdk.simulation.helper import payload_needs_decoding


class TestWorkflowSimulationService:
    """Test WorkflowSimulationService class."""

    def test_init_with_simulation_config(self):
        """Test initializing service with simulation config."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test_output"),
                    ),
                    nodes=["node1#1", "node2#1"],
                )
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        service = WorkflowSimulationService(sim_config)

        assert service.simulation_config == sim_config
        assert len(service.node_id_to_payload_map) == 0  # Empty until initialized

    def test_init_without_simulation_config(self):
        """Test initializing service without simulation config."""
        service = WorkflowSimulationService(None)

        assert service.simulation_config is None
        assert len(service.node_id_to_payload_map) == 0

    def test_init_with_multiple_strategies(self):
        """Test initializing service with multiple node strategies."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="output1"),
                    ),
                    nodes=["node1#1", "node2#1"],
                ),
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="output2"),
                    ),
                    nodes=["node3#1"],
                ),
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.TEMPORAL_HISTORY,
                        config=TemporalHistoryConfig(
                            reference_workflow_id="workflow-123",
                            reference_workflow_run_id="run-456",
                        ),
                    ),
                    nodes=["node4#1", "node5#1"],
                ),
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        service = WorkflowSimulationService(sim_config)

        assert service.simulation_config == sim_config
        assert len(service.node_id_to_payload_map) == 0  # Empty until initialized

    @pytest.mark.asyncio
    async def test_get_simulation_response_simulation_disabled(self):
        """Test getting simulation response when simulation is disabled."""
        service = WorkflowSimulationService(None)

        response = await service.get_simulation_response("node1")

        assert isinstance(response, SimulationResponse)
        assert response.execution_type == ExecutionType.EXECUTE
        assert response.execution_response is None

    @pytest.mark.asyncio
    async def test_get_simulation_response_node_found(self):
        """Test getting simulation response when node is found."""
        service = WorkflowSimulationService(None)
        service.node_id_to_payload_map = {
            "node1#1": NodePayload(node_id="node1#1", input_payload=None, output_payload="test_output")
        }

        with patch(
            "zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub.execute_activity", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MockedResultOutput(root="test_output")
            mock_execute.return_value = mock_result
            response = await service.get_simulation_response("node1#1")

            assert isinstance(response, SimulationResponse)
            assert response.execution_type == ExecutionType.MOCK
            assert response.execution_response == "test_output"

    @pytest.mark.asyncio
    async def test_get_simulation_response_node_not_found(self):
        """Test getting simulation response when node is not found."""
        service = WorkflowSimulationService(None)
        service.node_id_to_payload_map = {"node1#1": "test_output"}

        response = await service.get_simulation_response("nonexistent_node")

        assert isinstance(response, SimulationResponse)
        assert response.execution_type == ExecutionType.EXECUTE
        assert response.execution_response is None

    @pytest.mark.asyncio
    async def test_get_simulation_response_with_dict_output(self):
        """Test getting simulation response with dictionary output."""
        dict_output = {"key": "value", "number": 123, "list": [1, 2, 3]}

        service = WorkflowSimulationService(None)
        service.node_id_to_payload_map = {
            "node1#1": NodePayload(node_id="node1#1", input_payload=None, output_payload=dict_output)
        }

        with patch(
            "zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub.execute_activity", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MockedResultOutput(root=dict_output)
            mock_execute.return_value = mock_result
            response = await service.get_simulation_response("node1#1")

            assert isinstance(response, SimulationResponse)
            assert response.execution_type == ExecutionType.MOCK
            assert response.execution_response == dict_output

    @pytest.mark.asyncio
    async def test_get_simulation_response_with_list_output(self):
        """Test getting simulation response with list output."""
        list_output = [1, 2, 3, "test", {"nested": "value"}]

        service = WorkflowSimulationService(None)
        service.node_id_to_payload_map = {
            "node1#1": NodePayload(node_id="node1#1", input_payload=None, output_payload=list_output)
        }

        with patch(
            "zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub.execute_activity", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MockedResultOutput(root=list_output)
            mock_execute.return_value = mock_result
            response = await service.get_simulation_response("node1#1")

            assert isinstance(response, SimulationResponse)
            assert response.execution_type == ExecutionType.MOCK
            assert response.execution_response == list_output

    @pytest.mark.asyncio
    async def test_initialize_simulation_data_success(self):
        """Test successful initialization of simulation data."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test_output"),
                    ),
                    nodes=["node1#1"],
                )
            ]
        )
        sim_config = SimulationConfig(mock_config=mock_config)
        service = WorkflowSimulationService(sim_config)

        # Mock the workflow execution
        mock_workflow_result = Mock()
        mock_workflow_result.node_id_to_payload_map = {
            "node1#1": NodePayload(node_id="node1#1", input_payload=None, output_payload="test_output")
        }

        with patch("zamp_public_workflow_sdk.actions_hub.ActionsHub") as mock_actions_hub:
            mock_actions_hub.execute_child_workflow = AsyncMock(return_value=mock_workflow_result)
            mock_actions_hub.clear_node_id_tracker = Mock()

            await service._initialize_simulation_data(workflow_id="test_workflow_id", bucket_name="test-bucket")

            assert len(service.node_id_to_payload_map) == 1
            assert service.node_id_to_payload_map["node1#1"].output_payload == "test_output"
            mock_actions_hub.execute_child_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_simulation_data_workflow_failure(self):
        """Test initialization when workflow execution fails."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test_output"),
                    ),
                    nodes=["node1#1"],
                )
            ]
        )
        sim_config = SimulationConfig(mock_config=mock_config)
        service = WorkflowSimulationService(sim_config)

        with patch("zamp_public_workflow_sdk.actions_hub.ActionsHub") as mock_actions_hub:
            mock_actions_hub.execute_child_workflow = AsyncMock(side_effect=Exception("Workflow failed"))

            with pytest.raises(Exception):
                await service._initialize_simulation_data(workflow_id="test_workflow_id", bucket_name="test-bucket")

    @pytest.mark.asyncio
    async def test_initialize_simulation_data_none_result(self):
        """Test initialization when workflow returns None."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test_output"),
                    ),
                    nodes=["node1#1"],
                )
            ]
        )
        sim_config = SimulationConfig(mock_config=mock_config)
        service = WorkflowSimulationService(sim_config)

        with patch("zamp_public_workflow_sdk.actions_hub.ActionsHub") as mock_actions_hub:
            mock_actions_hub.execute_child_workflow = AsyncMock(return_value=None)

            with pytest.raises(AttributeError):
                await service._initialize_simulation_data(workflow_id="test_workflow_id", bucket_name="test-bucket")

    def test_payload_needs_decoding_with_encoding_metadata(self):
        """Test that payload with encoding metadata returns True."""
        payload = {"metadata": {"encoding": "json/plain"}, "data": "some_encoded_data"}

        assert payload_needs_decoding(payload) is True

    def test_payload_needs_decoding_with_different_encoding(self):
        """Test that payload with different encoding type returns True."""
        payload = {"metadata": {"encoding": "base64"}, "data": "encoded_content"}

        assert payload_needs_decoding(payload) is True

    def test_payload_needs_decoding_without_encoding_metadata(self):
        """Test that payload without encoding metadata returns False."""
        payload = {"metadata": {"other_field": "value"}, "data": "some_data"}

        assert payload_needs_decoding(payload) is False

    def test_payload_needs_decoding_with_none_encoding(self):
        """Test that payload with None encoding returns False."""
        payload = {"metadata": {"encoding": None}, "data": "some_data"}

        assert payload_needs_decoding(payload) is False

    def test_payload_needs_decoding_without_metadata(self):
        """Test that payload without metadata returns False."""
        payload = {"data": "some_data", "other_field": "value"}

        assert payload_needs_decoding(payload) is False

    def test_payload_needs_decoding_with_empty_metadata(self):
        """Test that payload with empty metadata returns False."""
        payload = {"metadata": {}, "data": "some_data"}

        assert payload_needs_decoding(payload) is False

    def test_payload_needs_decoding_non_dict_payload_string(self):
        """Test that non-dict payload (string) returns False."""
        payload = "plain_string_payload"

        assert payload_needs_decoding(payload) is False

    def test_payload_needs_decoding_non_dict_payload_list(self):
        """Test that non-dict payload (list) returns False."""
        payload = ["item1", "item2"]

        assert payload_needs_decoding(payload) is False

    def test_payload_needs_decoding_non_dict_payload_none(self):
        """Test that None payload returns False."""
        payload = None

        assert payload_needs_decoding(payload) is False

    def test_payload_needs_decoding_non_dict_payload_number(self):
        """Test that numeric payload returns False."""
        payload = 12345

        assert payload_needs_decoding(payload) is False

    def test_payload_needs_decoding_with_nested_metadata(self):
        """Test that payload with nested metadata structure works correctly."""
        payload = {"metadata": {"encoding": "json/plain", "nested": {"field": "value"}}, "data": "encoded_data"}

        assert payload_needs_decoding(payload) is True

    def test_payload_needs_decoding_with_empty_string_encoding(self):
        """Test that payload with empty string encoding returns False."""
        payload = {"metadata": {"encoding": ""}, "data": "some_data"}

        assert payload_needs_decoding(payload) is True

    def test_payload_needs_decoding_real_world_temporal_history(self):
        """Test with real-world Temporal History encoded payload structure."""
        payload = {
            "metadata": {"encoding": "json/plain", "messageType": "ActivityResult"},
            "data": "eyJyZXN1bHQiOiAidGVzdF9kYXRhIn0=",
        }

        assert payload_needs_decoding(payload) is True

    def test_payload_needs_decoding_real_world_custom_output(self):
        """Test with real-world Custom Output raw payload structure."""
        payload = {"key": "value", "number": 123, "list": [1, 2, 3]}

        assert payload_needs_decoding(payload) is False
