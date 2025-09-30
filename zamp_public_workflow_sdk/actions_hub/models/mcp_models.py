"""
MCP (Model Context Protocol) models for ActionsHub.

This module defines models for MCP configuration and access control
within the ActionsHub system.
"""

from typing import List, Dict
from pydantic import BaseModel, Field
from enum import Enum


class MCPAction(Enum):
    """MCP action types for service access control."""

    READ = "MCP_READ"
    WRITE = "MCP_WRITE"


class MCPAccessPattern(Enum):
    """MCP access string patterns for parsing."""

    READ_PATTERN = "R"
    WRITE_PATTERN = "W"


class MCPConfig(BaseModel):
    """MCP configuration for a service."""

    service_name: str = Field(
        ..., description="Name of the service (must match activity labels)"
    )
    accesses: List[MCPAction] = Field(
        default_factory=list,
        description="List of access types like [MCPAction.READ.value, MCPAction.WRITE.value]",
    )

    def to_mcp_labels(self) -> List[str]:
        """Convert to MCP label format for compatibility."""
        labels = [self.service_name]
        labels.extend([access.value for access in self.accesses])
        return labels

    @classmethod
    def from_access_string(cls, service_name: str, access_str: str) -> "MCPConfig":
        """Create from service:access string format."""
        access_str = access_str.upper().strip()

        accesses = []
        if MCPAccessPattern.READ_PATTERN.value in access_str:
            accesses.append(MCPAction.READ)
        if MCPAccessPattern.WRITE_PATTERN.value in access_str:
            accesses.append(MCPAction.WRITE)

        return cls(service_name=service_name.upper().strip(), accesses=accesses)


class MCPServiceConfig(BaseModel):
    """MCP service configuration containing multiple services and their access controls."""

    services: List[MCPConfig] = Field(
        default_factory=list, description="List of service configurations"
    )

    def add_service(self, service_name: str, access_str: str) -> None:
        """Add a service with access control."""
        access_control = MCPConfig.from_access_string(service_name, access_str)
        self.services.append(access_control)

    def get_service_labels(self) -> List[str]:
        """Get all service names that have any access."""
        return [service.service_name for service in self.services]

    def get_access_config(self) -> Dict[str, List[str]]:
        """Get access configuration in the format expected by tool registry."""
        config = {}
        for service in self.services:
            config[service.service_name] = [access.value for access in service.accesses]
        return config

    def has_access(self, service_name: str, access_type: str) -> bool:
        """Check if a service has specific access type."""
        for service in self.services:
            if service.service_name == service_name:
                return access_type in [access.value for access in service.accesses]
        return False
