"""
Unit tests for simulation validation models.
"""

import pytest
from pydantic import ValidationError

from zamp_public_workflow_sdk.simulation.models.simulation_validation import (
    NodeComparison,
    SimulationValidatorInput,
    SimulationValidatorOutput,
    MismatchedNodeSummary,
)
from zamp_public_workflow_sdk.simulation.models import (
    SimulationConfig,
    NodeMockConfig,
    NodeStrategy,
    SimulationStrategyConfig,
    StrategyType,
    CustomOutputConfig,
)
from zamp_public_workflow_sdk.actions_hub.models.common_models import ZampMetadataContext


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
        assert comparison.reference_input is None
        assert comparison.golden_input is None
        assert comparison.reference_output is None
        assert comparison.golden_output is None
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
            reference_input={"param": "value"},
            golden_input={"param": "value"},
            reference_output={"result": "success"},
            golden_output={"result": "success"},
        )

        assert comparison.inputs_match is True
        assert comparison.outputs_match is True
        assert comparison.reference_input == {"param": "value"}
        assert comparison.golden_input == {"param": "value"}
        assert comparison.reference_output == {"result": "success"}
        assert comparison.golden_output == {"result": "success"}

    def test_node_comparison_with_differences(self):
        """Test creating node comparison with input/output differences."""
        comparison = NodeComparison(
            node_id="activity#1",
            is_mocked=False,
            inputs_match=False,
            outputs_match=False,
            reference_input={"param": "value1"},
            golden_input={"param": "value2"},
            reference_output={"result": "success1"},
            golden_output={"result": "success2"},
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


class TestMismatchedNodeSummary:
    """Test MismatchedNodeSummary model."""

    def test_mismatched_node_summary_minimal(self):
        """Test creating minimal mismatched node summary."""
        summary = MismatchedNodeSummary(
            node_id="activity#1",
            inputs_match=False,
            outputs_match=True,
        )

        assert summary.node_id == "activity#1"
        assert summary.inputs_match is False
        assert summary.outputs_match is True
        assert summary.input_differences is None
        assert summary.output_differences is None

    def test_mismatched_node_summary_with_differences(self):
        """Test creating mismatched node summary with differences."""
        summary = MismatchedNodeSummary(
            node_id="activity#1",
            inputs_match=False,
            outputs_match=False,
            input_differences={"values_changed": {"root['param']": {"new_value": "value1", "old_value": "value2"}}},
            output_differences={
                "values_changed": {"root['result']": {"new_value": "success1", "old_value": "success2"}}
            },
        )

        assert summary.input_differences == {
            "values_changed": {"root['param']": {"new_value": "value1", "old_value": "value2"}}
        }
        assert summary.output_differences == {
            "values_changed": {"root['result']": {"new_value": "success1", "old_value": "success2"}}
        }

    def test_mismatched_node_summary_validation(self):
        """Test that mismatched node summary validates required fields."""
        with pytest.raises(ValidationError):
            MismatchedNodeSummary()  # Missing required fields

        with pytest.raises(ValidationError):
            MismatchedNodeSummary(
                node_id="activity#1",
                inputs_match=False,
                # Missing required outputs_match
            )

        with pytest.raises(ValidationError):
            MismatchedNodeSummary(
                inputs_match=False,
                outputs_match=True,
                # Missing required node_id
            )


class TestSimulationValidatorInput:
    """Test SimulationValidatorInput model."""

    def test_simulation_validator_input_valid(self):
        """Test creating valid simulation validator input."""
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
        simulation_config = SimulationConfig(mock_config=mock_config)
        metadata_context = ZampMetadataContext(organization_id="org-123", user_id="user-456", process_id="process-789")

        input_data = SimulationValidatorInput(
            reference_workflow_id="ref-workflow-123",
            reference_run_id="ref-run-456",
            golden_workflow_id="golden-workflow-789",
            golden_run_id="golden-run-012",
            simulation_config=simulation_config,
            zamp_metadata_context=metadata_context,
        )

        assert input_data.reference_workflow_id == "ref-workflow-123"
        assert input_data.reference_run_id == "ref-run-456"
        assert input_data.golden_workflow_id == "golden-workflow-789"
        assert input_data.golden_run_id == "golden-run-012"
        assert input_data.simulation_config == simulation_config
        assert input_data.zamp_metadata_context == metadata_context

    def test_simulation_validator_input_validation(self):
        """Test that simulation validator input validates required fields."""
        with pytest.raises(ValidationError):
            SimulationValidatorInput()  # Missing all required fields

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
        simulation_config = SimulationConfig(mock_config=mock_config)
        metadata_context = ZampMetadataContext(organization_id="org-123", user_id="user-456", process_id="process-789")

        # Test missing reference_workflow_id
        with pytest.raises(ValidationError):
            SimulationValidatorInput(
                reference_run_id="ref-run-456",
                golden_workflow_id="golden-workflow-789",
                golden_run_id="golden-run-012",
                simulation_config=simulation_config,
                zamp_metadata_context=metadata_context,
            )

        # Test missing simulation_config
        with pytest.raises(ValidationError):
            SimulationValidatorInput(
                reference_workflow_id="ref-workflow-123",
                reference_run_id="ref-run-456",
                golden_workflow_id="golden-workflow-789",
                golden_run_id="golden-run-012",
                zamp_metadata_context=metadata_context,
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
            error_nodes_count=0,
            comparisons=[],
            validation_passed=True,
        )

        assert output.total_nodes_compared == 0
        assert output.mocked_nodes_count == 0
        assert output.matching_nodes_count == 0
        assert output.mismatched_nodes_count == 0
        assert output.error_nodes_count == 0
        assert output.mismatched_nodes_summary == []
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

        mismatched_summary = MismatchedNodeSummary(
            node_id="activity#2",
            inputs_match=False,
            outputs_match=False,
            input_differences={"values_changed": {"root['param']": {"new_value": "value1", "old_value": "value2"}}},
            output_differences={
                "values_changed": {"root['result']": {"new_value": "success1", "old_value": "success2"}}
            },
        )

        output = SimulationValidatorOutput(
            total_nodes_compared=2,
            mocked_nodes_count=0,
            matching_nodes_count=1,
            mismatched_nodes_count=1,
            error_nodes_count=0,
            mismatched_nodes_summary=[mismatched_summary],
            comparisons=[comparison1, comparison2],
            validation_passed=False,
        )

        assert output.total_nodes_compared == 2
        assert output.mocked_nodes_count == 0
        assert output.matching_nodes_count == 1
        assert output.mismatched_nodes_count == 1
        assert output.error_nodes_count == 0
        assert len(output.mismatched_nodes_summary) == 1
        assert output.mismatched_nodes_summary[0].node_id == "activity#2"
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
                error_nodes_count=0,
                validation_passed=True,
            )

        # Test missing validation_passed
        with pytest.raises(ValidationError):
            SimulationValidatorOutput(
                total_nodes_compared=1,
                mocked_nodes_count=0,
                matching_nodes_count=1,
                mismatched_nodes_count=0,
                error_nodes_count=0,
                comparisons=[],
            )

    def test_simulation_validator_output_default_factory(self):
        """Test that mismatched_nodes_summary uses default_factory."""
        output = SimulationValidatorOutput(
            total_nodes_compared=0,
            mocked_nodes_count=0,
            matching_nodes_count=0,
            mismatched_nodes_count=0,
            error_nodes_count=0,
            comparisons=[],
            validation_passed=True,
        )

        # Should default to empty list
        assert output.mismatched_nodes_summary == []
        assert isinstance(output.mismatched_nodes_summary, list)
