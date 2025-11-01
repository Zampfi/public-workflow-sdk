"""
Integration tests for simulation workflows and services.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from zamp_public_workflow_sdk.simulation.constants import PayloadKey
from zamp_public_workflow_sdk.simulation.models import (
    CustomOutputConfig,
    NodeMockConfig,
    NodeStrategy,
    SimulationConfig,
    SimulationStrategyConfig,
    SimulationFetchDataWorkflowInput,
    SimulationFetchDataWorkflowOutput,
    StrategyType,
    TemporalHistoryConfig,
)
from zamp_public_workflow_sdk.simulation.models.simulation_response import (
    SimulationStrategyOutput,
)
from zamp_public_workflow_sdk.simulation.workflow_simulation_service import (
    WorkflowSimulationService,
)
from zamp_public_workflow_sdk.simulation.workflows.simulation_workflow import (
    SimulationFetchDataWorkflow,
)


class TestSimulationWorkflowIntegration:
    """Integration tests for SimulationFetchDataWorkflow."""

    def test_create_strategy_custom_output(self):
        """Test create_strategy method with custom output strategy."""
        node_strategy = NodeStrategy(
            strategy=SimulationStrategyConfig(
                type=StrategyType.CUSTOM_OUTPUT,
                config=CustomOutputConfig(output_value="test_output"),
            ),
            nodes=["node1#1"],
        )

        strategy = WorkflowSimulationService.get_strategy(node_strategy)

        assert strategy is not None
        assert strategy.output_value == "test_output"

    def test_create_strategy_temporal_history(self):
        """Test create_strategy method with temporal history strategy."""
        node_strategy = NodeStrategy(
            strategy=SimulationStrategyConfig(
                type=StrategyType.TEMPORAL_HISTORY,
                config=TemporalHistoryConfig(
                    reference_workflow_id="workflow-123",
                    reference_workflow_run_id="run-456",
                ),
            ),
            nodes=["node1#1"],
        )

        strategy = WorkflowSimulationService.get_strategy(node_strategy)

        assert strategy is not None
        assert strategy.reference_workflow_id == "workflow-123"
        assert strategy.reference_workflow_run_id == "run-456"

    def test_create_strategy_unknown_type(self):
        """Test create_strategy method with unknown strategy type."""
        # Create a mock node strategy with unknown type
        mock_node_strategy = Mock()
        mock_node_strategy.strategy.type = "UNKNOWN_TYPE"
        mock_node_strategy.strategy.config = CustomOutputConfig(output_value="test_output")

        with pytest.raises(ValueError, match="Unknown strategy type: UNKNOWN_TYPE"):
            WorkflowSimulationService.get_strategy(mock_node_strategy)

    @pytest.mark.asyncio
    async def test_execute_with_custom_output_strategies(self):
        """Test execute method with custom output strategies."""
        workflow = SimulationFetchDataWorkflow()

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
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        input_data = SimulationFetchDataWorkflowInput(simulation_config=sim_config)

        result = await workflow.execute(input_data)

        assert isinstance(result, SimulationFetchDataWorkflowOutput)
        assert len(result.node_id_to_response_map) == 3
        assert result.node_id_to_response_map["node1#1"] == "output1"
        assert result.node_id_to_response_map["node2#1"] == "output1"
        assert result.node_id_to_response_map["node3#1"] == "output2"

    @pytest.mark.asyncio
    async def test_execute_with_temporal_history_strategies(self):
        """Test execute method with temporal history strategies."""
        workflow = SimulationFetchDataWorkflow()

        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.TEMPORAL_HISTORY,
                        config=TemporalHistoryConfig(
                            reference_workflow_id="workflow-123",
                            reference_workflow_run_id="run-456",
                        ),
                    ),
                    nodes=["node1#1", "node2#1"],
                ),
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        input_data = SimulationFetchDataWorkflowInput(simulation_config=sim_config)

        # Mock the temporal history strategy at the point where it's created
        with patch(
            "zamp_public_workflow_sdk.simulation.workflow_simulation_service.TemporalHistoryStrategyHandler"
        ) as mock_handler_class:
            mock_strategy = Mock()
            mock_strategy.execute = AsyncMock(
                return_value=SimulationStrategyOutput(
                    node_outputs={
                        "node1#1": "history_output",
                        "node2#1": "history_output",
                    }
                )
            )
            mock_handler_class.return_value = mock_strategy

            result = await workflow.execute(input_data)

            assert isinstance(result, SimulationFetchDataWorkflowOutput)
            assert len(result.node_id_to_response_map) == 2
            assert result.node_id_to_response_map["node1#1"] == "history_output"
            assert result.node_id_to_response_map["node2#1"] == "history_output"

    @pytest.mark.asyncio
    async def test_execute_with_mixed_strategies(self):
        """Test execute method with mixed strategy types."""
        workflow = SimulationFetchDataWorkflow()

        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="custom_output"),
                    ),
                    nodes=["node1#1"],
                ),
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.TEMPORAL_HISTORY,
                        config=TemporalHistoryConfig(
                            reference_workflow_id="workflow-123",
                            reference_workflow_run_id="run-456",
                        ),
                    ),
                    nodes=["node2#1"],
                ),
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        input_data = SimulationFetchDataWorkflowInput(simulation_config=sim_config)

        # Mock the temporal history strategy at the point where it's created
        with patch(
            "zamp_public_workflow_sdk.simulation.workflow_simulation_service.TemporalHistoryStrategyHandler"
        ) as mock_handler_class:
            mock_strategy = Mock()
            mock_strategy.execute = AsyncMock(
                return_value=SimulationStrategyOutput(node_outputs={"node2#1": "history_output"})
            )
            mock_handler_class.return_value = mock_strategy

            result = await workflow.execute(input_data)

            assert isinstance(result, SimulationFetchDataWorkflowOutput)
            assert len(result.node_id_to_response_map) == 2
            assert result.node_id_to_response_map["node1#1"] == "custom_output"
            assert result.node_id_to_response_map["node2#1"] == "history_output"

    @pytest.mark.asyncio
    async def test_execute_strategy_execution_failure(self):
        """Test execute method when strategy execution fails."""
        workflow = SimulationFetchDataWorkflow()

        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test_output"),
                    ),
                    nodes=["node1#1"],
                ),
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        input_data = SimulationFetchDataWorkflowInput(simulation_config=sim_config)

        # Mock strategy to raise exception at the point where it's created
        with patch(
            "zamp_public_workflow_sdk.simulation.workflow_simulation_service.CustomOutputStrategyHandler"
        ) as mock_handler_class:
            mock_strategy = Mock()
            mock_strategy.execute = AsyncMock(side_effect=Exception("Strategy failed"))
            mock_handler_class.return_value = mock_strategy

            result = await workflow.execute(input_data)

            assert isinstance(result, SimulationFetchDataWorkflowOutput)
            assert len(result.node_id_to_response_map) == 0  # No successful executions

    @pytest.mark.asyncio
    async def test_execute_strategy_returns_empty_outputs(self):
        """Test execute method when strategy returns empty node_outputs."""
        workflow = SimulationFetchDataWorkflow()

        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test_output"),
                    ),
                    nodes=["node1#1"],
                ),
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        input_data = SimulationFetchDataWorkflowInput(simulation_config=sim_config)

        # Mock strategy to return empty node_outputs at the point where it's created
        with patch(
            "zamp_public_workflow_sdk.simulation.workflow_simulation_service.CustomOutputStrategyHandler"
        ) as mock_handler_class:
            mock_strategy = Mock()
            mock_strategy.execute = AsyncMock(return_value=SimulationStrategyOutput(node_outputs={}))
            mock_handler_class.return_value = mock_strategy

            result = await workflow.execute(input_data)

            assert isinstance(result, SimulationFetchDataWorkflowOutput)
            assert len(result.node_id_to_response_map) == 0  # No mock outputs

    @pytest.mark.asyncio
    async def test_execute_strategy_returns_none_output(self):
        """Test execute method when strategy returns None output."""
        workflow = SimulationFetchDataWorkflow()

        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test_output"),
                    ),
                    nodes=["node1#1"],
                ),
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        input_data = SimulationFetchDataWorkflowInput(simulation_config=sim_config)

        # Mock strategy to return None output at the point where it's created
        with patch(
            "zamp_public_workflow_sdk.simulation.workflow_simulation_service.CustomOutputStrategyHandler"
        ) as mock_handler_class:
            mock_strategy = Mock()
            mock_strategy.execute = AsyncMock(return_value=SimulationStrategyOutput(node_outputs={}))
            mock_handler_class.return_value = mock_strategy

            result = await workflow.execute(input_data)

            assert isinstance(result, SimulationFetchDataWorkflowOutput)
            assert len(result.node_id_to_response_map) == 0  # No mock outputs


class TestSimulationServiceIntegration:
    """Integration tests for WorkflowSimulationService with real workflows."""

    @pytest.mark.asyncio
    async def test_initialize_simulation_data_integration(self):
        """Test full integration of simulation data initialization."""
        from zamp_public_workflow_sdk.simulation.workflow_simulation_service import (
            WorkflowSimulationService,
        )

        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="integration_test_output"),
                    ),
                    nodes=["integration_node#1"],
                ),
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        service = WorkflowSimulationService(sim_config)

        # Mock the workflow execution - note the new data structure with input/output payloads
        mock_workflow_result = Mock()
        mock_workflow_result.node_id_to_response_map = {
            "integration_node#1": {PayloadKey.INPUT_PAYLOAD: None, PayloadKey.OUTPUT_PAYLOAD: "integration_test_output"}
        }

        with patch("zamp_public_workflow_sdk.actions_hub.ActionsHub") as mock_actions_hub:
            mock_actions_hub.execute_child_workflow = AsyncMock(return_value=mock_workflow_result)
            mock_actions_hub.clear_node_id_tracker = Mock()
            # Also patch execute_activity for the get_simulation_response call
            from zamp_public_workflow_sdk.simulation.models.mocked_result import MockedResultOutput

            mock_actions_hub.execute_activity = AsyncMock(
                return_value=MockedResultOutput(output="integration_test_output")
            )

            await service._initialize_simulation_data()

            assert len(service.node_id_to_response_map) == 1
            assert (
                service.node_id_to_response_map["integration_node#1"][PayloadKey.OUTPUT_PAYLOAD]
                == "integration_test_output"
            )

            # Test that simulation response works - mock ActionsHub.execute_activity since get_simulation_response now calls return_mocked_result
            response = await service.get_simulation_response("integration_node#1")
            assert response is not None
            assert response.execution_type.value == "MOCK"
            assert response.execution_response == "integration_test_output"
