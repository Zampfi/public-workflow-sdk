"""
Unit tests for WorkflowSimulationService.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from zamp_public_workflow_sdk.simulation.models import (
    CustomOutputConfig,
    ExecutionType,
    NodeMockConfig,
    NodeStrategy,
    SimulationConfig,
    SimulationResponse,
    SimulationStrategyConfig,
    StrategyType,
    TemporalHistoryConfig,
)
from zamp_public_workflow_sdk.simulation.workflow_simulation_service import (
    WorkflowSimulationService,
)


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
        assert len(service.node_id_to_response_map) == 0  # Empty until initialized

    def test_init_without_simulation_config(self):
        """Test initializing service without simulation config."""
        service = WorkflowSimulationService(None)

        assert service.simulation_config is None
        assert len(service.node_id_to_response_map) == 0

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
        assert len(service.node_id_to_response_map) == 0  # Empty until initialized

    def test_get_simulation_response_simulation_disabled(self):
        """Test getting simulation response when simulation is disabled."""
        service = WorkflowSimulationService(None)

        response = service.get_simulation_response("node1")

        assert isinstance(response, SimulationResponse)
        assert response.execution_type == ExecutionType.EXECUTE
        assert response.execution_response is None

    def test_get_simulation_response_node_found(self):
        """Test getting simulation response when node is found."""
        service = WorkflowSimulationService(None)
        service.node_id_to_response_map = {"node1#1": "test_output"}

        response = service.get_simulation_response("node1#1")

        assert isinstance(response, SimulationResponse)
        assert response.execution_type == ExecutionType.MOCK
        assert response.execution_response == "test_output"

    def test_get_simulation_response_node_not_found(self):
        """Test getting simulation response when node is not found."""
        service = WorkflowSimulationService(None)
        service.node_id_to_response_map = {"node1#1": "test_output"}

        response = service.get_simulation_response("nonexistent_node")

        assert isinstance(response, SimulationResponse)
        assert response.execution_type == ExecutionType.EXECUTE
        assert response.execution_response is None

    def test_get_simulation_response_with_dict_output(self):
        """Test getting simulation response with dictionary output."""
        dict_output = {"key": "value", "number": 123, "list": [1, 2, 3]}

        service = WorkflowSimulationService(None)
        service.node_id_to_response_map = {"node1#1": dict_output}

        response = service.get_simulation_response("node1#1")

        assert isinstance(response, SimulationResponse)
        assert response.execution_type == ExecutionType.MOCK
        assert response.execution_response == dict_output

    def test_get_simulation_response_with_list_output(self):
        """Test getting simulation response with list output."""
        list_output = [1, 2, 3, "test", {"nested": "value"}]

        service = WorkflowSimulationService(None)
        service.node_id_to_response_map = {"node1#1": list_output}

        response = service.get_simulation_response("node1#1")

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
        mock_workflow_result.node_id_to_response_map = {"node1#1": "test_output"}

        with patch("zamp_public_workflow_sdk.actions_hub.ActionsHub") as mock_actions_hub:
            mock_actions_hub.execute_child_workflow = AsyncMock(return_value=mock_workflow_result)
            mock_actions_hub.clear_node_id_tracker = Mock()

            await service._initialize_simulation_data()

            assert len(service.node_id_to_response_map) == 1
            assert service.node_id_to_response_map["node1#1"] == "test_output"
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

            with pytest.raises(Exception, match="Workflow failed"):
                await service._initialize_simulation_data()

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
                await service._initialize_simulation_data()
