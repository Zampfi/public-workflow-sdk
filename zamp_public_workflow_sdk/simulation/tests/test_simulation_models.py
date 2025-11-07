"""
Unit tests for simulation models.
"""

import pytest
from pydantic import ValidationError

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


class TestStrategyType:
    """Test StrategyType enum."""

    def test_strategy_type_values(self):
        """Test that strategy type values are correct."""
        assert StrategyType.TEMPORAL_HISTORY == "TEMPORAL_HISTORY"
        assert StrategyType.CUSTOM_OUTPUT == "CUSTOM_OUTPUT"

    def test_strategy_type_enum_behavior(self):
        """Test that strategy type behaves as string enum."""
        assert isinstance(StrategyType.TEMPORAL_HISTORY, str)
        # For string enums, the value should be the string itself
        assert StrategyType.TEMPORAL_HISTORY == "TEMPORAL_HISTORY"


class TestExecutionType:
    """Test ExecutionType enum."""

    def test_execution_type_values(self):
        """Test that execution type values are correct."""
        assert ExecutionType.EXECUTE == "EXECUTE"
        assert ExecutionType.MOCK == "MOCK"

    def test_execution_type_enum_behavior(self):
        """Test that execution type behaves as string enum."""
        assert isinstance(ExecutionType.MOCK, str)
        # For string enums, the value should be the string itself
        assert ExecutionType.MOCK == "MOCK"


class TestSimulationResponse:
    """Test SimulationResponse model."""

    def test_simulation_response_mock(self):
        """Test creating simulation response with MOCK execution type."""
        response = SimulationResponse(execution_type=ExecutionType.MOCK, execution_response="test_output")

        assert response.execution_type == ExecutionType.MOCK
        assert response.execution_response == "test_output"

    def test_simulation_response_execute(self):
        """Test creating simulation response with EXECUTE execution type."""
        response = SimulationResponse(execution_type=ExecutionType.EXECUTE, execution_response=None)

        assert response.execution_type == ExecutionType.EXECUTE
        assert response.execution_response is None

    def test_simulation_response_validation(self):
        """Test that simulation response validates required fields."""
        with pytest.raises(ValidationError):
            SimulationResponse()  # Missing required execution_type

        with pytest.raises(ValidationError):
            SimulationResponse(execution_type="INVALID_TYPE")


class TestTemporalHistoryConfig:
    """Test TemporalHistoryConfig model."""

    def test_temporal_history_config_valid(self):
        """Test creating valid temporal history config."""
        config = TemporalHistoryConfig(reference_workflow_id="workflow-123", reference_workflow_run_id="run-456")

        assert config.reference_workflow_id == "workflow-123"
        assert config.reference_workflow_run_id == "run-456"

    def test_temporal_history_config_validation(self):
        """Test that temporal history config validates required fields."""
        with pytest.raises(ValidationError):
            TemporalHistoryConfig()  # Missing required fields

        with pytest.raises(ValidationError):
            TemporalHistoryConfig(
                reference_workflow_id="workflow-123"
                # Missing reference_workflow_run_id
            )


class TestCustomOutputConfig:
    """Test CustomOutputConfig model."""

    def test_custom_output_config_string(self):
        """Test creating custom output config with string value."""
        config = CustomOutputConfig(output_value="test_string")
        assert config.output_value == "test_string"

    def test_custom_output_config_dict(self):
        """Test creating custom output config with dict value."""
        config = CustomOutputConfig(output_value={"key": "value", "number": 123})
        assert config.output_value == {"key": "value", "number": 123}

    def test_custom_output_config_list(self):
        """Test creating custom output config with list value."""
        config = CustomOutputConfig(output_value=[1, 2, 3, "test"])
        assert config.output_value == [1, 2, 3, "test"]

    def test_custom_output_config_validation(self):
        """Test that custom output config validates required fields."""
        with pytest.raises(ValidationError):
            CustomOutputConfig()  # Missing required output_value


class TestSimulationStrategyConfig:
    """Test SimulationStrategyConfig model."""

    def test_temporal_history_strategy(self):
        """Test creating temporal history strategy config."""
        temporal_config = TemporalHistoryConfig(
            reference_workflow_id="workflow-123", reference_workflow_run_id="run-456"
        )

        strategy = SimulationStrategyConfig(type=StrategyType.TEMPORAL_HISTORY, config=temporal_config)

        assert strategy.type == StrategyType.TEMPORAL_HISTORY
        assert isinstance(strategy.config, TemporalHistoryConfig)
        assert strategy.config.reference_workflow_id == "workflow-123"

    def test_custom_output_strategy(self):
        """Test creating custom output strategy config."""
        custom_config = CustomOutputConfig(output_value="test_output")

        strategy = SimulationStrategyConfig(type=StrategyType.CUSTOM_OUTPUT, config=custom_config)

        assert strategy.type == StrategyType.CUSTOM_OUTPUT
        assert isinstance(strategy.config, CustomOutputConfig)
        assert strategy.config.output_value == "test_output"

    def test_strategy_config_validation(self):
        """Test that strategy config validates required fields."""
        with pytest.raises(ValidationError):
            SimulationStrategyConfig()  # Missing required fields

        with pytest.raises(ValidationError):
            SimulationStrategyConfig(
                type=StrategyType.TEMPORAL_HISTORY,
                config="invalid_config",  # Should be TemporalHistoryConfig
            )


class TestNodeStrategy:
    """Test NodeStrategy model."""

    def test_node_strategy_valid(self):
        """Test creating valid node strategy."""
        strategy_config = SimulationStrategyConfig(
            type=StrategyType.CUSTOM_OUTPUT,
            config=CustomOutputConfig(output_value="test"),
        )

        node_strategy = NodeStrategy(
            strategy=strategy_config,
            nodes=["node1#1", "node2#1", "parent.child.node3#1"],
        )

        assert len(node_strategy.nodes) == 3
        assert "node1#1" in node_strategy.nodes
        assert node_strategy.strategy.type == StrategyType.CUSTOM_OUTPUT

    def test_node_strategy_validation(self):
        """Test that node strategy validates required fields."""
        with pytest.raises(ValidationError):
            NodeStrategy()  # Missing required fields

        with pytest.raises(ValidationError):
            NodeStrategy(
                strategy="invalid_strategy",  # Should be SimulationStrategyConfig
                nodes=["node1#1"],
            )


class TestNodeMockConfig:
    """Test NodeMockConfig model."""

    def test_mock_config_valid(self):
        """Test creating valid mock config."""
        node_strategies = [
            NodeStrategy(
                strategy=SimulationStrategyConfig(
                    type=StrategyType.CUSTOM_OUTPUT,
                    config=CustomOutputConfig(output_value="output1"),
                ),
                nodes=["node1#1", "node2#1"],
            ),
            NodeStrategy(
                strategy=SimulationStrategyConfig(
                    type=StrategyType.TEMPORAL_HISTORY,
                    config=TemporalHistoryConfig(
                        reference_workflow_id="workflow-123",
                        reference_workflow_run_id="run-456",
                    ),
                ),
                nodes=["node3#1"],
            ),
        ]

        mock_config = NodeMockConfig(node_strategies=node_strategies)

        assert len(mock_config.node_strategies) == 2
        assert mock_config.node_strategies[0].nodes == ["node1#1", "node2#1"]
        assert mock_config.node_strategies[1].strategy.type == StrategyType.TEMPORAL_HISTORY

    def test_mock_config_validation(self):
        """Test that mock config validates required fields."""
        with pytest.raises(ValidationError):
            NodeMockConfig()  # Missing required node_strategies


class TestSimulationConfig:
    """Test SimulationConfig model."""

    def test_simulation_config_valid(self):
        """Test creating valid simulation config."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test"),
                    ),
                    nodes=["node1#1"],
                )
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)

        assert sim_config.version == "1.0.0"  # Default value
        assert sim_config.mock_config == mock_config

    def test_simulation_config_custom_version(self):
        """Test creating simulation config with custom version."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test"),
                    ),
                    nodes=["dummy#1"],
                )
            ]
        )

        # Test that only version 1.0.0 is supported
        with pytest.raises(ValidationError):
            SimulationConfig(version="2.0.0", mock_config=mock_config)

    def test_simulation_config_validation(self):
        """Test that simulation config validates required fields."""
        with pytest.raises(ValidationError):
            SimulationConfig()  # Missing required mock_config

    def test_simulation_config_no_overlap_valid(self):
        """Test that simulation config accepts non-overlapping nodes."""
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
                        type=StrategyType.TEMPORAL_HISTORY,
                        config=TemporalHistoryConfig(
                            reference_workflow_id="workflow-123",
                            reference_workflow_run_id="run-456",
                        ),
                    ),
                    nodes=["node3#1", "node4#1"],
                ),
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        assert sim_config.mock_config == mock_config

    def test_simulation_config_exact_duplicate_nodes(self):
        """Test that simulation config rejects exact duplicate nodes across strategies."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="output1"),
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
                    nodes=["node1#1"],
                ),
            ]
        )

        with pytest.raises(ValueError, match="Duplicate node 'node1#1' found in configuration"):
            SimulationConfig(mock_config=mock_config)

    def test_simulation_config_hierarchical_overlap_parent_in_custom(self):
        """Test that simulation config rejects hierarchical overlap when parent is in CUSTOM_OUTPUT."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="output1"),
                    ),
                    nodes=["Workflow#1.ChildWorkflow#1"],
                ),
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.TEMPORAL_HISTORY,
                        config=TemporalHistoryConfig(
                            reference_workflow_id="workflow-123",
                            reference_workflow_run_id="run-456",
                        ),
                    ),
                    nodes=["Workflow#1.ChildWorkflow#1.Activity#1"],
                ),
            ]
        )

        with pytest.raises(ValueError, match="Hierarchical overlap detected"):
            SimulationConfig(mock_config=mock_config)

    def test_simulation_config_hierarchical_overlap_parent_in_temporal(self):
        """Test that simulation config rejects hierarchical overlap when parent is in TEMPORAL_HISTORY."""
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
                    nodes=["Workflow#1.ChildWorkflow#1"],
                ),
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="output1"),
                    ),
                    nodes=["Workflow#1.ChildWorkflow#1.Activity#1"],
                ),
            ]
        )

        with pytest.raises(ValueError, match="Hierarchical overlap detected"):
            SimulationConfig(mock_config=mock_config)

    def test_simulation_config_hierarchical_overlap_nested_workflows(self):
        """Test that simulation config rejects hierarchical overlap with deeply nested workflows."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="output1"),
                    ),
                    nodes=[
                        "EnhancedStripeInvoiceProcessingWorkflow#1.POBackedInvoiceProcessingWorkflow#1.ContractExtractionWorkflow#1"
                    ],
                ),
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.TEMPORAL_HISTORY,
                        config=TemporalHistoryConfig(
                            reference_workflow_id="workflow-123",
                            reference_workflow_run_id="run-456",
                        ),
                    ),
                    nodes=[
                        "EnhancedStripeInvoiceProcessingWorkflow#1.POBackedInvoiceProcessingWorkflow#1.ContractExtractionWorkflow#1.query_internal_blob_storage#1"
                    ],
                ),
            ]
        )

        with pytest.raises(ValueError, match="Hierarchical overlap detected"):
            SimulationConfig(mock_config=mock_config)

    def test_simulation_config_rejects_same_node_in_same_strategy(self):
        """Test that simulation config rejects duplicate nodes even within the same strategy."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="output1"),
                    ),
                    nodes=["node1#1", "node1#1"],  # Same node twice
                ),
            ]
        )

        # Should raise an error - duplicates are not allowed even in same strategy
        with pytest.raises(ValueError, match="Duplicate node 'node1#1' found in configuration"):
            SimulationConfig(mock_config=mock_config)

    def test_simulation_config_allows_parallel_nodes(self):
        """Test that simulation config allows parallel nodes that don't overlap."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="output1"),
                    ),
                    nodes=["Workflow#1.Activity#1"],
                ),
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.TEMPORAL_HISTORY,
                        config=TemporalHistoryConfig(
                            reference_workflow_id="workflow-123",
                            reference_workflow_run_id="run-456",
                        ),
                    ),
                    nodes=["Workflow#1.Activity#2"],  # Different activity, no overlap
                ),
            ]
        )

        sim_config = SimulationConfig(mock_config=mock_config)
        assert sim_config.mock_config == mock_config

    def test_simulation_config_multiple_overlaps(self):
        """Test that simulation config detects the first overlap when multiple exist."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="output1"),
                    ),
                    nodes=["Workflow#1", "Workflow#2"],
                ),
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.TEMPORAL_HISTORY,
                        config=TemporalHistoryConfig(
                            reference_workflow_id="workflow-123",
                            reference_workflow_run_id="run-456",
                        ),
                    ),
                    nodes=["Workflow#1.Activity#1", "Workflow#2.Activity#1"],
                ),
            ]
        )

        with pytest.raises(ValueError, match="Hierarchical overlap detected"):
            SimulationConfig(mock_config=mock_config)
