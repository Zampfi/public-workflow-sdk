"""
Strategy models for simulation system.

This module contains models related to simulation strategies and their configurations.
"""

import re
from typing import Any, List, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class StrategyType(str, Enum):
    """Types of simulation strategies available."""

    TEMPORAL_HISTORY = "TEMPORAL_HISTORY"
    CUSTOM_OUTPUT = "CUSTOM_OUTPUT"


class TemporalHistoryConfig(BaseModel):
    """Configuration for temporal history strategy."""

    reference_workflow_id: str = Field(
        ..., description="Reference workflow ID to fetch history from", min_length=1
    )
    reference_workflow_run_id: str = Field(
        ..., description="Reference run ID to fetch history from", min_length=1
    )


class CustomOutputConfig(BaseModel):
    """Configuration for custom output strategy."""

    output_value: Any = Field(..., description="The custom output value to return")


class SimulationStrategyConfig(BaseModel):
    """Configuration for a simulation strategy."""

    type: StrategyType = Field(..., description="Type of strategy to use")
    config: Union[TemporalHistoryConfig, CustomOutputConfig] = Field(
        ..., description="Strategy-specific configuration"
    )

    @model_validator(mode="after")
    def validate_strategy_type_and_config(self):
        """Validate that strategy type matches the config type."""
        if self.type == StrategyType.TEMPORAL_HISTORY and not isinstance(
            self.config, TemporalHistoryConfig
        ):
            raise ValueError("Temporal history strategy requires TemporalHistoryConfig")

        if self.type == StrategyType.CUSTOM_OUTPUT and not isinstance(
            self.config, CustomOutputConfig
        ):
            raise ValueError("Custom output strategy requires CustomOutputConfig")

        return self

    class Config:
        """Pydantic config."""

        use_enum_values = True


class NodeStrategy(BaseModel):
    """Strategy configuration for specific nodes."""

    strategy: SimulationStrategyConfig = Field(
        ..., description="Simulation strategy configuration"
    )
    nodes: List[str] = Field(
        ..., description="List of node IDs this strategy applies to", min_length=1
    )

    @field_validator("nodes")
    @classmethod
    def validate_node_ids(cls, v):
        """Validate each node ID follows the format 'Str#number'."""
        node_id_pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.-]*#[1-9]\d*$")

        for i, node_id in enumerate(v):
            if not node_id or not node_id.strip():
                raise ValueError(f"Node ID at index {i} cannot be empty or whitespace")

            trimmed = node_id.strip()
            if not node_id_pattern.match(trimmed):
                raise ValueError(
                    f"Node ID at index {i} must be in format 'Str#number' (e.g., 'activity#1'), got: {trimmed}"
                )
        return v
