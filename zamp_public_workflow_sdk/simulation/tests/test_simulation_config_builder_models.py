"""Unit tests for simulation config builder models."""

import pytest
from pydantic import ValidationError

from zamp_public_workflow_sdk.simulation.models.simulation_config_builder import (
    SimulationConfigBuilderInput,
    SimulationConfigBuilderOutput,
)
from zamp_public_workflow_sdk.simulation.models import (
    SimulationConfig,
    NodeMockConfig,
    NodeStrategy,
    SimulationStrategyConfig,
    TemporalHistoryConfig,
    StrategyType,
)


class TestSimulationConfigBuilderInput:
    """Test cases for SimulationConfigBuilderInput."""

    def test_valid_input(self):
        """Test creating valid input."""
        input_data = SimulationConfigBuilderInput(
            workflow_id="test-workflow-id",
            run_id="test-run-id",
        )

        assert input_data.workflow_id == "test-workflow-id"
        assert input_data.run_id == "test-run-id"

    def test_missing_workflow_id(self):
        """Test validation error when workflow_id is missing."""
        with pytest.raises(ValidationError):
            SimulationConfigBuilderInput(
                run_id="test-run-id",
            )

    def test_missing_run_id(self):
        """Test validation error when run_id is missing."""
        with pytest.raises(ValidationError):
            SimulationConfigBuilderInput(
                workflow_id="test-workflow-id",
            )

    def test_empty_workflow_id(self):
        """Test validation error when workflow_id is empty."""
        input_data = SimulationConfigBuilderInput(
            workflow_id="",
            run_id="test-run-id",
        )
        assert input_data.workflow_id == ""

    def test_empty_run_id(self):
        """Test validation error when run_id is empty."""
        input_data = SimulationConfigBuilderInput(
            workflow_id="test-workflow-id",
            run_id="",
        )
        assert input_data.run_id == ""

    def test_workflow_id_description(self):
        """Test workflow_id field description."""
        field_info = SimulationConfigBuilderInput.model_fields["workflow_id"]
        assert "Workflow ID to extract node IDs from" in field_info.description

    def test_run_id_description(self):
        """Test run_id field description."""
        field_info = SimulationConfigBuilderInput.model_fields["run_id"]
        assert "Run ID to extract node IDs from" in field_info.description


class TestSimulationConfigBuilderOutput:
    """Test cases for SimulationConfigBuilderOutput."""

    def test_valid_output(self):
        """Test creating valid output."""
        simulation_config = SimulationConfig(
            version="1.0.0",
            mock_config=NodeMockConfig(node_strategies=[]),
        )

        output = SimulationConfigBuilderOutput(
            simulation_config=simulation_config,
        )

        assert output.simulation_config == simulation_config
        assert output.simulation_config.version == "1.0.0"

    def test_missing_simulation_config(self):
        """Test validation error when simulation_config is missing."""
        with pytest.raises(ValidationError):
            SimulationConfigBuilderOutput()

    def test_simulation_config_description(self):
        """Test simulation_config field description."""
        field_info = SimulationConfigBuilderOutput.model_fields["simulation_config"]
        assert "Generated simulation configuration" in field_info.description

    def test_output_with_complete_simulation_config(self):
        """Test output with complete simulation configuration."""
        # Create a complete simulation config
        node_strategy = NodeStrategy(
            strategy=SimulationStrategyConfig(
                type=StrategyType.TEMPORAL_HISTORY,
                config=TemporalHistoryConfig(
                    reference_workflow_id="ref-workflow-id",
                    reference_workflow_run_id="ref-run-id",
                ),
            ),
            nodes=["node1", "node2", "node3"],
        )

        mock_config = NodeMockConfig(node_strategies=[node_strategy])
        simulation_config = SimulationConfig(
            version="1.0.0",
            mock_config=mock_config,
        )

        output = SimulationConfigBuilderOutput(
            simulation_config=simulation_config,
        )

        assert output.simulation_config.version == "1.0.0"
        assert len(output.simulation_config.mock_config.node_strategies) == 1
        assert output.simulation_config.mock_config.node_strategies[0].nodes == ["node1", "node2", "node3"]
        assert output.simulation_config.mock_config.node_strategies[0].strategy.type == StrategyType.TEMPORAL_HISTORY

    def test_output_serialization(self):
        """Test output can be serialized to dict."""
        simulation_config = SimulationConfig(
            version="1.0.0",
            mock_config=NodeMockConfig(node_strategies=[]),
        )

        output = SimulationConfigBuilderOutput(
            simulation_config=simulation_config,
        )

        output_dict = output.model_dump()
        assert "simulation_config" in output_dict
        assert output_dict["simulation_config"]["version"] == "1.0.0"

    def test_output_from_dict(self):
        """Test output can be created from dict."""
        data = {"simulation_config": {"version": "1.0.0", "mock_config": {"node_strategies": []}}}

        output = SimulationConfigBuilderOutput.model_validate(data)
        assert output.simulation_config.version == "1.0.0"
        assert len(output.simulation_config.mock_config.node_strategies) == 0
