"""
Response models for simulation system.

This module contains models related to simulation responses and execution types.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ExecutionType(str, Enum):
    """Types of execution for simulation responses."""

    EXECUTE = "EXECUTE"
    MOCK = "MOCK"


class SimulationResponse(BaseModel):
    """Response from simulation system indicating how to handle an activity execution."""

    execution_type: ExecutionType = Field(
        ..., description="Type of execution (EXECUTE or MOCK)"
    )
    execution_response: Optional[Any] = Field(
        None, description="Mocked response data if execution_type is MOCK"
    )


class SimulationStrategyOutput(BaseModel):
    """Output from a simulation strategy execution."""

    node_outputs: Dict[str, Optional[Any]] = Field(
        default_factory=dict,
        description="Dictionary mapping node IDs to their mocked outputs, or empty dict if no mocking",
    )
