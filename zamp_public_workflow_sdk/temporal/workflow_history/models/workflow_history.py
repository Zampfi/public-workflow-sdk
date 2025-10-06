from typing import List, Optional, Dict
from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import (
    NodePayloadData,
)
from zamp_public_workflow_sdk.temporal.workflow_history.helpers import (
    get_input_from_node_id,
    get_output_from_node_id,
    get_node_data_from_node_id,
    extract_node_payloads,
)


class WorkflowHistory(BaseModel):
    workflow_id: str = Field(..., description="Unique identifier for the workflow")
    run_id: str = Field(..., description="Unique identifier for the workflow run")
    events: List[dict] = Field(..., description="List of workflow events")

    def get_node_input(self, node_id: str) -> Optional[dict]:
        """
        Get input payload for a specific node ID.

        Args:
            node_id: The node ID to get input for

        Returns:
            Input payload data if found, None otherwise
        """
        return get_input_from_node_id(self.events, node_id)

    def get_node_output(self, node_id: str) -> Optional[dict]:
        """
        Get output payload for a specific node ID.

        Args:
            node_id: The node ID to get output for

        Returns:
            Output payload data if found, None otherwise
        """
        return get_output_from_node_id(self.events, node_id)

    def get_node_data(self, node_id: str) -> Dict[str, "NodePayloadData"]:
        """
        Get all node data (including input/output payloads and all events) for a specific node ID.

        Args:
            node_id: The node ID to get data for

        Returns:
            Dictionary with node_id as key and NodePayloadData as value
        """
        return get_node_data_from_node_id(self.events, node_id)

    def get_nodes_data(
        self, target_node_ids: Optional[List[str]] = None
    ) -> Dict[str, "NodePayloadData"]:
        """
        Get all node data (including input/output payloads and all events) from the workflow events.

        Args:
            target_node_ids: Optional list of node IDs to filter by

        Returns:
            Dictionary mapping node_id to NodePayloadData
        """
        return extract_node_payloads(self.events, target_node_ids)
