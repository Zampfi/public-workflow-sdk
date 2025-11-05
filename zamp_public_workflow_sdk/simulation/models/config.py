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
        """Validate that no node appears in multiple strategies or overlaps hierarchically."""
        nodes_with_strategy = []

        for strategy_index, strategy in enumerate(self.mock_config.node_strategies):
            for node_id in strategy.nodes:
                nodes_with_strategy.append((strategy_index, node_id))

        for current_position, (current_strategy_index, current_node_id) in enumerate(nodes_with_strategy):
            for next_strategy_index, next_node_id in nodes_with_strategy[current_position + 1 :]:
                if current_strategy_index == next_strategy_index:
                    continue
                # Check if the nodes are the same
                if current_node_id == next_node_id:
                    raise ValueError(
                        f"Node '{current_node_id}' appears in multiple strategies: "
                        f"strategy[{current_strategy_index}] and strategy[{next_strategy_index}]"
                    )

                # Check if the nodes are hierarchical
                if not (
                    current_node_id.startswith(next_node_id + ".") or next_node_id.startswith(current_node_id + ".")
                ):
                    continue

                raise ValueError(
                    f"Hierarchical overlap detected: node '{current_node_id}' in strategy[{current_strategy_index}] "
                    f"overlaps with node '{next_node_id}' in strategy[{next_strategy_index}]"
                )

        return self

    class Config:
        """Pydantic config."""

        use_enum_values = True
