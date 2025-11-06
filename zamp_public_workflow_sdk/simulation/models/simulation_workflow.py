from typing import Any
from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.actions_hub.models.common_models import (
    ZampMetadataContext,
)
from zamp_public_workflow_sdk.simulation.models import SimulationConfig
from zamp_public_workflow_sdk.simulation.models.node_payload_models import (
    NodePayloadResult,
    NodePayloadType,
)


class SimulationOutputSchema(BaseModel):
    """Schema defining which activities to extract and what data to return.

    Maps node IDs to payload types to specify which activity inputs/outputs
    should be extracted from workflow history.

    Example:
        {
            "gmail_search_messages#1": "INPUT_OUTPUT",
            "parse_email#3": "OUTPUT",
            "upload_to_s3#5": "INPUT"
        }
    """

    node_payloads: dict[str, NodePayloadType] = Field(
        description="Map of node IDs to payload types (INPUT, OUTPUT, or INPUT_OUTPUT)"
    )


class SimulationWorkflowInput(BaseModel):
    """Input parameters for SimulationWorkflow.

    Defines which workflow to execute, its parameters, simulation configuration,
    and which activity data to extract.
    """

    workflow_name: str = Field(
        description="Fully qualified name of the workflow to execute (e.g., 'StripeFetchInvoicesWorkflow')"
    )
    workflow_params: dict[str, Any] = Field(description="Parameters to pass to the original workflow execution")
    simulation_config: SimulationConfig = Field(description="Simulation configuration with mock settings")
    output_schema: SimulationOutputSchema = Field(
        description="Schema defining which activities to extract and what data to return"
    )
    zamp_metadata_context: ZampMetadataContext | None = Field(
        default=None, description="Metadata context for logging and tracing"
    )


class SimulationWorkflowOutput(BaseModel):
    """Output from SimulationWorkflow execution.

    Contains a list of extracted activity payload data, each with node_id and optionally input/output.
    """

    node_payloads: list[NodePayloadResult] = Field(
        description="List of extracted activity payloads with their inputs and/or outputs"
    )
