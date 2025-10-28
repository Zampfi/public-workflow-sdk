"""Models for workflow validation system."""

from typing import Any
from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.simulation.models import SimulationConfig


class NodeComparison(BaseModel):
    """Comparison result for a single node."""

    node_id: str = Field(..., description="Node ID being compared")
    is_mocked: bool = Field(..., description="Whether the node is mocked in simulation_config")
    inputs_match: bool | None = Field(
        default=None,
        description="Whether inputs match (None if node is mocked or comparison skipped)",
    )
    outputs_match: bool | None = Field(
        default=None,
        description="Whether outputs match (None if node is mocked or comparison skipped)",
    )
    actual_input: Any = Field(
        default=None,
        description="Input from simulation workflow (can be dict, list, str, etc.)",
    )
    expected_input: Any = Field(
        default=None,
        description="Input from golden workflow (can be dict, list, str, etc.)",
    )
    actual_output: Any = Field(
        default=None,
        description="Output from simulation workflow (can be dict, list, str, etc.)",
    )
    expected_output: Any = Field(
        default=None,
        description="Output from golden workflow (can be dict, list, str, etc.)",
    )
    difference: dict[str, Any] | None = Field(
        default=None,
        description="Differences between inputs (only populated if inputs don't match)",
    )
    output_difference: dict[str, Any] | None = Field(
        default=None,
        description="Differences between outputs (only populated if outputs don't match)",
    )
    error: str | None = Field(default=None, description="Error message if comparison failed")


class SimulationValidatorInput(BaseModel):
    """Input for workflow simulation validation."""

    simulation_workflow_id: str = Field(
        ...,
        description="Workflow ID of the workflow running with simulation (mocked workflow)",
    )
    simulation_workflow_run_id: str = Field(
        ...,
        description="Run ID of the workflow running with simulation (mocked workflow)",
    )
    golden_workflow_id: str = Field(
        ...,
        description="Workflow ID of the golden workflow (original execution without mocking)",
    )
    golden_run_id: str = Field(
        ...,
        description="Run ID of the golden workflow (original execution without mocking)",
    )
    simulation_config: SimulationConfig = Field(..., description="Simulation config used in the simulation workflow")


class SimulationValidatorOutput(BaseModel):
    """Output for workflow simulation validation."""

    total_nodes_compared: int = Field(..., description="Total number of nodes compared")
    mocked_nodes_count: int = Field(..., description="Number of nodes that were mocked (skipped from comparison)")
    matching_nodes_count: int = Field(..., description="Number of non-mocked nodes with matching inputs")
    mismatched_nodes_count: int = Field(..., description="Number of non-mocked nodes with mismatched inputs")
    mismatched_node_ids: list[str] | None = Field(default=None, description="List of node IDs that had mismatches")
    comparison_error_nodes_count: int = Field(..., description="Number of nodes where comparison failed with error")
    comparison_error_node_ids: list[str] | None = Field(
        default=None, description="List of node IDs where comparison failed"
    )
    nodes_missing_in_simulation_workflow: list[str] | None = Field(
        default=None, description="List of node IDs missing in simulation workflow"
    )
    nodes_missing_in_golden_workflow: list[str] | None = Field(
        default=None, description="List of node IDs missing in golden workflow"
    )
    comparisons: list[NodeComparison] = Field(..., description="Detailed comparison results for each node")
    validation_passed: bool = Field(..., description="Whether all non-mocked nodes have matching inputs")
