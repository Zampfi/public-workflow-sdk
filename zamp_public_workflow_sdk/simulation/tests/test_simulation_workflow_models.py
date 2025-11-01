"""
Unit tests for simulation workflow models.

This module tests the Pydantic models for SimulationCodeWorkflow.
"""

import pytest
from pydantic import ValidationError

from zamp_public_workflow_sdk.actions_hub.models.common_models import ZampMetadataContext
from zamp_public_workflow_sdk.simulation.models import SimulationConfig, NodeMockConfig
from zamp_public_workflow_sdk.simulation.models.simulation_workflow import (
    NodeCaptureMode,
    SimulationOutputSchema,
    NodeCaptureResult,
    SimulationWorkflowInput,
    SimulationWorkflowOutput,
)


class TestNodeCaptureMode:
    """Test NodeCaptureMode enum."""

    def test_node_capture_mode_values(self):
        """Test that node capture mode values are correct."""
        assert NodeCaptureMode.INPUT == "INPUT"
        assert NodeCaptureMode.OUTPUT == "OUTPUT"
        assert NodeCaptureMode.INPUT_OUTPUT == "INPUT_OUTPUT"

    def test_node_capture_mode_enum_behavior(self):
        """Test that node capture mode behaves as string enum."""
        assert isinstance(NodeCaptureMode.INPUT, str)
        assert isinstance(NodeCaptureMode.OUTPUT, str)
        assert isinstance(NodeCaptureMode.INPUT_OUTPUT, str)
        # For string enums, the value should be the string itself
        assert NodeCaptureMode.INPUT == "INPUT"
        assert NodeCaptureMode.OUTPUT == "OUTPUT"
        assert NodeCaptureMode.INPUT_OUTPUT == "INPUT_OUTPUT"


class TestSimulationOutputSchema:
    """Test SimulationOutputSchema model."""

    def test_simulation_output_schema_valid(self):
        """Test creating valid simulation output schema."""
        schema = SimulationOutputSchema(
            node_captures={
                "activity#1": NodeCaptureMode.INPUT,
                "activity#2": NodeCaptureMode.OUTPUT,
                "activity#3": NodeCaptureMode.INPUT_OUTPUT,
            }
        )

        assert len(schema.node_captures) == 3
        assert schema.node_captures["activity#1"] == NodeCaptureMode.INPUT
        assert schema.node_captures["activity#2"] == NodeCaptureMode.OUTPUT
        assert schema.node_captures["activity#3"] == NodeCaptureMode.INPUT_OUTPUT

    def test_simulation_output_schema_empty(self):
        """Test creating simulation output schema with empty node_captures."""
        schema = SimulationOutputSchema(node_captures={})

        assert len(schema.node_captures) == 0
        assert schema.node_captures == {}

    def test_simulation_output_schema_missing_field(self):
        """Test validation error when node_captures is missing."""
        with pytest.raises(ValidationError):
            SimulationOutputSchema()  # Missing required node_captures field

    def test_simulation_output_schema_with_string_values(self):
        """Test that string values can be used for node capture modes."""
        schema = SimulationOutputSchema(
            node_captures={
                "activity#1": "INPUT",
                "activity#2": "OUTPUT",
                "activity#3": "INPUT_OUTPUT",
            }
        )

        assert schema.node_captures["activity#1"] == NodeCaptureMode.INPUT
        assert schema.node_captures["activity#2"] == NodeCaptureMode.OUTPUT
        assert schema.node_captures["activity#3"] == NodeCaptureMode.INPUT_OUTPUT


class TestNodeCaptureResult:
    """Test NodeCaptureResult model."""

    def test_node_capture_result_with_both_input_output(self):
        """Test creating node capture result with both input and output."""
        result = NodeCaptureResult(
            node_id="activity#1",
            input={"param1": "value1"},
            output={"result": "success"},
        )

        assert result.node_id == "activity#1"
        assert result.input == {"param1": "value1"}
        assert result.output == {"result": "success"}

    def test_node_capture_result_with_input_only(self):
        """Test creating node capture result with input only."""
        result = NodeCaptureResult(
            node_id="activity#2",
            input={"param1": "value1"},
        )

        assert result.node_id == "activity#2"
        assert result.input == {"param1": "value1"}
        assert result.output is None

    def test_node_capture_result_with_output_only(self):
        """Test creating node capture result with output only."""
        result = NodeCaptureResult(
            node_id="activity#3",
            output={"result": "success"},
        )

        assert result.node_id == "activity#3"
        assert result.input is None
        assert result.output == {"result": "success"}

    def test_node_capture_result_with_none_values(self):
        """Test creating node capture result with None values."""
        result = NodeCaptureResult(
            node_id="activity#4",
            input=None,
            output=None,
        )

        assert result.node_id == "activity#4"
        assert result.input is None
        assert result.output is None

    def test_node_capture_result_missing_node_id(self):
        """Test validation error when node_id is missing."""
        with pytest.raises(ValidationError):
            NodeCaptureResult()  # Missing required node_id field

    def test_node_capture_result_with_complex_data(self):
        """Test creating node capture result with complex data types."""
        result = NodeCaptureResult(
            node_id="activity#5",
            input={"nested": {"key": "value"}, "list": [1, 2, 3]},
            output={"status": True, "count": 42},
        )

        assert result.node_id == "activity#5"
        assert result.input == {"nested": {"key": "value"}, "list": [1, 2, 3]}
        assert result.output == {"status": True, "count": 42}


class TestSimulationWorkflowInput:
    """Test SimulationWorkflowInput model."""

    def test_simulation_workflow_input_valid(self):
        """Test creating valid simulation workflow input."""
        simulation_config = SimulationConfig(mock_config=NodeMockConfig(node_strategies=[]))
        output_schema = SimulationOutputSchema(node_captures={"activity#1": NodeCaptureMode.INPUT_OUTPUT})

        input_data = SimulationWorkflowInput(
            workflow_name="TestWorkflow",
            workflow_params={"param1": "value1"},
            simulation_config=simulation_config,
            output_schema=output_schema,
        )

        assert input_data.workflow_name == "TestWorkflow"
        assert input_data.workflow_params == {"param1": "value1"}
        assert input_data.simulation_config == simulation_config
        assert input_data.output_schema == output_schema
        assert input_data.zamp_metadata_context is None

    def test_simulation_workflow_input_with_metadata_context(self):
        """Test creating simulation workflow input with metadata context."""
        simulation_config = SimulationConfig(mock_config=NodeMockConfig(node_strategies=[]))
        output_schema = SimulationOutputSchema(node_captures={"activity#1": NodeCaptureMode.OUTPUT})
        metadata_context = ZampMetadataContext(
            organization_id="org-123",
            user_id="user-456",
            process_id="proc-789",
        )

        input_data = SimulationWorkflowInput(
            workflow_name="TestWorkflow",
            workflow_params={},
            simulation_config=simulation_config,
            output_schema=output_schema,
            zamp_metadata_context=metadata_context,
        )

        assert input_data.zamp_metadata_context == metadata_context

    def test_simulation_workflow_input_missing_workflow_name(self):
        """Test validation error when workflow_name is missing."""
        simulation_config = SimulationConfig(mock_config=NodeMockConfig(node_strategies=[]))
        output_schema = SimulationOutputSchema(node_captures={})

        with pytest.raises(ValidationError):
            SimulationWorkflowInput(
                workflow_params={},
                simulation_config=simulation_config,
                output_schema=output_schema,
            )  # Missing required workflow_name

    def test_simulation_workflow_input_missing_workflow_params(self):
        """Test validation error when workflow_params is missing."""
        simulation_config = SimulationConfig(mock_config=NodeMockConfig(node_strategies=[]))
        output_schema = SimulationOutputSchema(node_captures={})

        with pytest.raises(ValidationError):
            SimulationWorkflowInput(
                workflow_name="TestWorkflow",
                simulation_config=simulation_config,
                output_schema=output_schema,
            )  # Missing required workflow_params

    def test_simulation_workflow_input_missing_simulation_config(self):
        """Test validation error when simulation_config is missing."""
        output_schema = SimulationOutputSchema(node_captures={})

        with pytest.raises(ValidationError):
            SimulationWorkflowInput(
                workflow_name="TestWorkflow",
                workflow_params={},
                output_schema=output_schema,
            )  # Missing required simulation_config

    def test_simulation_workflow_input_missing_output_schema(self):
        """Test validation error when output_schema is missing."""
        simulation_config = SimulationConfig(mock_config=NodeMockConfig(node_strategies=[]))

        with pytest.raises(ValidationError):
            SimulationWorkflowInput(
                workflow_name="TestWorkflow",
                workflow_params={},
                simulation_config=simulation_config,
            )  # Missing required output_schema

    def test_simulation_workflow_input_empty_workflow_params(self):
        """Test creating simulation workflow input with empty workflow_params."""
        simulation_config = SimulationConfig(mock_config=NodeMockConfig(node_strategies=[]))
        output_schema = SimulationOutputSchema(node_captures={})

        input_data = SimulationWorkflowInput(
            workflow_name="TestWorkflow",
            workflow_params={},
            simulation_config=simulation_config,
            output_schema=output_schema,
        )

        assert input_data.workflow_params == {}


class TestSimulationWorkflowOutput:
    """Test SimulationWorkflowOutput model."""

    def test_simulation_workflow_output_valid(self):
        """Test creating valid simulation workflow output."""
        node_captures = {
            "activity#1": NodeCaptureResult(
                node_id="activity#1",
                input={"param": "value"},
                output={"result": "success"},
            ),
            "activity#2": NodeCaptureResult(
                node_id="activity#2",
                output={"result": "done"},
            ),
        }

        output = SimulationWorkflowOutput(node_captures=node_captures)

        assert len(output.node_captures) == 2
        assert output.node_captures["activity#1"].node_id == "activity#1"
        assert output.node_captures["activity#1"].input == {"param": "value"}
        assert output.node_captures["activity#1"].output == {"result": "success"}
        assert output.node_captures["activity#2"].node_id == "activity#2"
        assert output.node_captures["activity#2"].input is None
        assert output.node_captures["activity#2"].output == {"result": "done"}

    def test_simulation_workflow_output_empty(self):
        """Test creating simulation workflow output with empty node_captures."""
        output = SimulationWorkflowOutput(node_captures={})

        assert len(output.node_captures) == 0
        assert output.node_captures == {}

    def test_simulation_workflow_output_missing_field(self):
        """Test validation error when node_captures is missing."""
        with pytest.raises(ValidationError):
            SimulationWorkflowOutput()  # Missing required node_captures field

    def test_simulation_workflow_output_multiple_nodes(self):
        """Test creating simulation workflow output with multiple node captures."""
        node_captures = {
            f"activity#{i}": NodeCaptureResult(
                node_id=f"activity#{i}",
                input={"index": i},
                output={"result": i * 2},
            )
            for i in range(1, 6)
        }

        output = SimulationWorkflowOutput(node_captures=node_captures)

        assert len(output.node_captures) == 5
        for i in range(1, 6):
            assert output.node_captures[f"activity#{i}"].node_id == f"activity#{i}"
            assert output.node_captures[f"activity#{i}"].input == {"index": i}
            assert output.node_captures[f"activity#{i}"].output == {"result": i * 2}
