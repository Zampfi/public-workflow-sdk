"""
Models for SimulationCodeWorkflow.

This module contains Pydantic models for executing workflows in simulation mode
and capturing activity inputs/outputs.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.actions_hub.models.common_models import (
    ZampMetadataContext,
)
from zamp_public_workflow_sdk.simulation.models import SimulationConfig


class NodeCaptureMode(str, Enum):
    """Mode for capturing activity data from workflow history."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    INPUT_OUTPUT = "INPUT_OUTPUT"


class SimulationOutputSchema(BaseModel):
    """Schema defining which activities to capture and what data to return.

    Maps node IDs to capture modes to specify which activity inputs/outputs
    should be extracted from workflow history.

    Example:
        {
            "gmail_search_messages#1": "INPUT_OUTPUT",
            "parse_email#3": "OUTPUT",
            "upload_to_s3#5": "INPUT"
        }
    """

    node_captures: Dict[str, NodeCaptureMode] = Field(
        description="Map of node IDs to capture modes (INPUT, OUTPUT, or INPUT_OUTPUT)"
    )


class NodeCaptureResult(BaseModel):
    """Result for a single activity capture from workflow history.

    Contains the captured input and/or output data for an activity execution.
    """

    node_id: str = Field(
        description="Node ID of the activity (e.g., 'activity_name#1')"
    )
    input: Optional[Any] = Field(
        default=None,
        description="Activity input parameters if captured (based on capture mode)",
    )
    output: Optional[Any] = Field(
        default=None,
        description="Activity output result if captured (based on capture mode)",
    )


class SimulationWorkflowInput(BaseModel):
    """Input parameters for SimulationCodeWorkflow.

    Defines which workflow to execute, its parameters, simulation configuration,
    and which activity data to capture.
    """

    workflow_name: str = Field(
        description="Fully qualified name of the workflow to execute (e.g., 'StripeFetchInvoicesWorkflow')"
    )
    workflow_params: Dict[str, Any] = Field(
        description="Parameters to pass to the original workflow execution"
    )
    simulation_config: SimulationConfig = Field(
        description="Simulation configuration with mock settings"
    )
    output_schema: SimulationOutputSchema = Field(
        description="Schema defining which activities to capture and what data to return"
    )
    zamp_metadata_context: Optional[ZampMetadataContext] = Field(
        default=None, description="Metadata context for logging and tracing"
    )



class SimulationWorkflowOutput(BaseModel):
    """Output from SimulationCodeWorkflow execution.

    Contains the workflow result, captured activity data, and workflow identifiers.
    """

    node_captures: Dict[str, NodeCaptureResult] = Field(
        description="Captured activity data indexed by node_id"
    )
