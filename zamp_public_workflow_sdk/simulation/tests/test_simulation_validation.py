"""
Unit tests for simulation validation models.
"""

import pytest
from pydantic import ValidationError

from zamp_public_workflow_sdk.simulation.models.simulation_validation import (
    NodeComparison,
    SimulationValidatorInput,
    SimulationValidatorOutput,
)
from zamp_public_workflow_sdk.simulation.models import (
    SimulationConfig,
    NodeMockConfig,
    NodeStrategy,
    SimulationStrategyConfig,
    StrategyType,
    CustomOutputConfig,
)


class TestNodeComparison:
    """Test NodeComparison model."""

    def test_node_comparison_minimal(self):
        """Test creating minimal node comparison."""
        comparison = NodeComparison(
            node_id="activity#1",
            is_mocked=True,
        )

        assert comparison.node_id == "activity#1"
        assert comparison.is_mocked is True
        assert comparison.inputs_match is None
        assert comparison.outputs_match is None
        assert comparison.actual_input is None
        assert comparison.expected_input is None
        assert comparison.actual_output is None
        assert comparison.expected_output is None
        assert comparison.difference is None
        assert comparison.output_difference is None
        assert comparison.error is None

    def test_node_comparison_with_matches(self):
        """Test creating node comparison with matching inputs/outputs."""
        comparison = NodeComparison(
            node_id="activity#1",
            is_mocked=False,
            inputs_match=True,
            outputs_match=True,
            actual_input={"param": "value"},
            expected_input={"param": "value"},
            actual_output={"result": "success"},
            expected_output={"result": "success"},
        )

        assert comparison.inputs_match is True
        assert comparison.outputs_match is True
        assert comparison.actual_input == {"param": "value"}
        assert comparison.expected_input == {"param": "value"}
        assert comparison.actual_output == {"result": "success"}
        assert comparison.expected_output == {"result": "success"}

    def test_node_comparison_with_differences(self):
        """Test creating node comparison with input/output differences."""
        comparison = NodeComparison(
            node_id="activity#1",
            is_mocked=False,
            inputs_match=False,
            outputs_match=False,
            actual_input={"param": "value1"},
            expected_input={"param": "value2"},
            actual_output={"result": "success1"},
            expected_output={"result": "success2"},
            difference={"values_changed": {"root['param']": {"new_value": "value1", "old_value": "value2"}}},
            output_difference={
                "values_changed": {"root['result']": {"new_value": "success1", "old_value": "success2"}}
            },
        )

        assert comparison.inputs_match is False
        assert comparison.outputs_match is False
        assert comparison.difference == {
            "values_changed": {"root['param']": {"new_value": "value1", "old_value": "value2"}}
        }
        assert comparison.output_difference == {
            "values_changed": {"root['result']": {"new_value": "success1", "old_value": "success2"}}
        }

    def test_node_comparison_with_error(self):
        """Test creating node comparison with error."""
        comparison = NodeComparison(
            node_id="activity#1",
            is_mocked=False,
            error="Node not found in reference workflow",
        )

        assert comparison.error == "Node not found in reference workflow"
        assert comparison.inputs_match is None
        assert comparison.outputs_match is None

    def test_node_comparison_validation(self):
        """Test that node comparison validates required fields."""
        with pytest.raises(ValidationError):
            NodeComparison()  # Missing required node_id and is_mocked

        with pytest.raises(ValidationError):
            NodeComparison(node_id="activity#1")  # Missing required is_mocked

        with pytest.raises(ValidationError):
            NodeComparison(is_mocked=True)  # Missing required node_id


class TestSimulationValidatorInput:
    """Test SimulationValidatorInput model."""

    def test_simulation_validator_input_valid(self):
        """Test creating valid simulation validator input."""
        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test", input_value="test"),
                    ),
                    nodes=["node1#1"],
                )
            ]
        )
        simulation_config = SimulationConfig(mock_config=mock_config)

        input_data = SimulationValidatorInput(
            simulation_workflow_id="sim-workflow-123",
            simulation_workflow_run_id="sim-run-456",
            golden_workflow_id="golden-workflow-789",
            golden_run_id="golden-run-012",
            simulation_config=simulation_config,
        )

        assert input_data.simulation_workflow_id == "sim-workflow-123"
        assert input_data.simulation_workflow_run_id == "sim-run-456"
        assert input_data.golden_workflow_id == "golden-workflow-789"
        assert input_data.golden_run_id == "golden-run-012"
        assert input_data.simulation_config == simulation_config

    def test_simulation_validator_input_validation(self):
        """Test that simulation validator input validates required fields."""
        with pytest.raises(ValidationError):
            SimulationValidatorInput()  # Missing all required fields

        mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test", input_value="test"),
                    ),
                    nodes=["node1#1"],
                )
            ]
        )
        simulation_config = SimulationConfig(mock_config=mock_config)

        # Test missing simulation_workflow_id
        with pytest.raises(ValidationError):
            SimulationValidatorInput(
                simulation_workflow_run_id="sim-run-456",
                golden_workflow_id="golden-workflow-789",
                golden_run_id="golden-run-012",
                simulation_config=simulation_config,
            )

        # Test missing simulation_config
        with pytest.raises(ValidationError):
            SimulationValidatorInput(
                simulation_workflow_id="sim-workflow-123",
                simulation_workflow_run_id="sim-run-456",
                golden_workflow_id="golden-workflow-789",
                golden_run_id="golden-run-012",
            )


class TestSimulationValidatorOutput:
    """Test SimulationValidatorOutput model."""

    def test_simulation_validator_output_minimal(self):
        """Test creating minimal simulation validator output."""
        output = SimulationValidatorOutput(
            total_nodes_compared=0,
            mocked_nodes_count=0,
            matching_nodes_count=0,
            mismatched_nodes_count=0,
            mismatched_node_ids=None,
            comparison_error_nodes_count=0,
            comparison_error_node_ids=None,
            nodes_missing_in_simulation_workflow=None,
            nodes_missing_in_golden_workflow=None,
            comparisons=[],
            validation_passed=True,
        )

        assert output.total_nodes_compared == 0
        assert output.mocked_nodes_count == 0
        assert output.matching_nodes_count == 0
        assert output.mismatched_nodes_count == 0
        assert output.mismatched_node_ids is None
        assert output.comparison_error_nodes_count == 0
        assert output.comparison_error_node_ids is None
        assert output.nodes_missing_in_simulation_workflow is None
        assert output.nodes_missing_in_golden_workflow is None
        assert output.comparisons == []
        assert output.validation_passed is True

    def test_simulation_validator_output_with_data(self):
        """Test creating simulation validator output with data."""
        comparison1 = NodeComparison(
            node_id="activity#1",
            is_mocked=False,
            inputs_match=True,
            outputs_match=True,
        )
        comparison2 = NodeComparison(
            node_id="activity#2",
            is_mocked=False,
            inputs_match=False,
            outputs_match=False,
            difference={"values_changed": {"root['param']": {"new_value": "value1", "old_value": "value2"}}},
            output_difference={
                "values_changed": {"root['result']": {"new_value": "success1", "old_value": "success2"}}
            },
        )

        output = SimulationValidatorOutput(
            total_nodes_compared=2,
            mocked_nodes_count=0,
            matching_nodes_count=1,
            mismatched_nodes_count=1,
            mismatched_node_ids=["activity#2"],
            comparison_error_nodes_count=0,
            comparison_error_node_ids=None,
            nodes_missing_in_simulation_workflow=None,
            nodes_missing_in_golden_workflow=None,
            comparisons=[comparison1, comparison2],
            validation_passed=False,
        )

        assert output.total_nodes_compared == 2
        assert output.mocked_nodes_count == 0
        assert output.matching_nodes_count == 1
        assert output.mismatched_nodes_count == 1
        assert output.mismatched_node_ids == ["activity#2"]
        assert output.comparison_error_nodes_count == 0
        assert output.comparison_error_node_ids is None
        assert output.nodes_missing_in_simulation_workflow is None
        assert output.nodes_missing_in_golden_workflow is None
        assert len(output.comparisons) == 2
        assert output.comparisons[0].node_id == "activity#1"
        assert output.comparisons[1].node_id == "activity#2"
        assert output.validation_passed is False

    def test_simulation_validator_output_validation(self):
        """Test that simulation validator output validates required fields."""
        with pytest.raises(ValidationError):
            SimulationValidatorOutput()  # Missing all required fields

        # Test missing comparisons
        with pytest.raises(ValidationError):
            SimulationValidatorOutput(
                total_nodes_compared=1,
                mocked_nodes_count=0,
                matching_nodes_count=1,
                mismatched_nodes_count=0,
                mismatched_node_ids=None,
                comparison_error_nodes_count=0,
                comparison_error_node_ids=None,
                nodes_missing_in_simulation_workflow=None,
                nodes_missing_in_golden_workflow=None,
                validation_passed=True,
            )

        # Test missing validation_passed
        with pytest.raises(ValidationError):
            SimulationValidatorOutput(
                total_nodes_compared=1,
                mocked_nodes_count=0,
                matching_nodes_count=1,
                mismatched_nodes_count=0,
                mismatched_node_ids=None,
                comparison_error_nodes_count=0,
                comparison_error_node_ids=None,
                nodes_missing_in_simulation_workflow=None,
                nodes_missing_in_golden_workflow=None,
                comparisons=[],
            )
