"""
Configuration models for simulation system.

This module contains models related to simulation configuration and node mocking.
"""

from typing import List
from pydantic import BaseModel, Field

from .simulation_strategy import NodeStrategy
from ..constants.versions import SupportedVersions


class NodeMockConfig(BaseModel):
    """Configuration for mocking nodes."""

    node_strategies: List[NodeStrategy] = Field(
        ..., description="List of node strategies"
    )


class SimulationConfig(BaseModel):
    """Root configuration for simulation settings."""

    version: SupportedVersions = Field(
        default=SupportedVersions.V1_0_0, description="Configuration version"
    )
    mock_config: NodeMockConfig = Field(
        ..., description="Configuration for mocking nodes"
    )

    class Config:
        """Pydantic config."""

        use_enum_values = True
