"""
Configuration models for simulation system.

This module contains models related to simulation configuration and node mocking.
"""

from typing import List
from pydantic import BaseModel, Field, model_validator

from .simulation_strategy import NodeStrategy
from ..constants.versions import SupportedVersions


class NodeMockConfig(BaseModel):
    """Configuration for mocking nodes."""

    node_strategies: List[NodeStrategy] = Field(
        ..., description="List of node strategies"
    )

    @model_validator(mode="after")
    def validate_node_strategies(self):
        """Validate node strategies list and check for duplicate nodes."""
        if not self.node_strategies:
            raise ValueError("Node strategies list cannot be empty")

        return self


class SimulationConfig(BaseModel):
    """Root configuration for simulation settings."""

    version: str = Field(
        default="1.0.0", description="Configuration version", min_length=1
    )
    mock_config: NodeMockConfig = Field(
        ..., description="Configuration for mocking nodes"
    )

    class Config:
        """Pydantic config."""

        use_enum_values = True

    @model_validator(mode="after")
    def validate_version(self):
        """Validate version is in supported versions list."""
        version = self.version.strip()
        if version not in [v.value for v in SupportedVersions]:
            supported_versions = [v.value for v in SupportedVersions]
            raise ValueError(
                f"Version '{version}' is not supported. Supported versions: {supported_versions}"
            )

        self.version = version
        return self
