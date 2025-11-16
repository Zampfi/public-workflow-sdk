"""
Response models for simulation system.

This module contains models related to simulation responses and execution types.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload


class ExecutionType(str, Enum):
    """Types of execution for simulation responses."""

    EXECUTE = "EXECUTE"
    MOCK = "MOCK"


class SimulationResponse(BaseModel):
    """Response from simulation system indicating how to handle an activity execution."""

    execution_type: ExecutionType = Field(..., description="Type of execution (EXECUTE or MOCK)")
    execution_response: Any | None = Field(None, description="Mocked response data if execution_type is MOCK")


class SimulationStrategyOutput(BaseModel):
    """Output from a simulation strategy execution."""

    node_id_to_payload_map: dict[str, NodePayload] = Field(
        default_factory=dict,
        description="Dictionary mapping node IDs to their mocked NodePayload instances, or empty dict if no mocking",
    )
