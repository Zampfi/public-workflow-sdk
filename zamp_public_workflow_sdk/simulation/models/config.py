"""
Configuration models for simulation system.

This module contains models related to simulation configuration and node mocking.
"""

from pydantic import BaseModel, Field, model_validator

from ..constants.versions import SupportedVersions
from .simulation_strategy import NodeStrategy


class NodeMockConfig(BaseModel):
    """Configuration for mocking nodes."""

    node_strategies: list[NodeStrategy] = Field(..., description="List of node strategies")


class SimulationConfig(BaseModel):
    """Root configuration for simulation settings."""

    version: SupportedVersions = Field(default=SupportedVersions.V1_0_0, description="Configuration version")
    mock_config: NodeMockConfig = Field(..., description="Configuration for mocking nodes")

    @model_validator(mode="after")
    def validate_no_overlapping_nodes(self):
        """Validate that no node appears multiple times or overlaps hierarchically."""
        node_set = set()

        for node_id in (node for strategy in self.mock_config.node_strategies for node in strategy.nodes):
            # Check for duplicate nodes
            if node_id in node_set:
                raise ValueError(f"Duplicate node '{node_id}' found in configuration")

            # Check for hierarchical overlaps
            for existing_node_id in node_set:
                if node_id.startswith(existing_node_id + ".") or existing_node_id.startswith(node_id + "."):
                    raise ValueError(
                        f"Hierarchical overlap detected: node '{node_id}' overlaps with node '{existing_node_id}'"
                    )
            node_set.add(node_id)

        return self

    class Config:
        """Pydantic config."""

        use_enum_values = True
