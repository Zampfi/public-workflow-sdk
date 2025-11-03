from pydantic import BaseModel, Field

from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload
from zamp_public_workflow_sdk.temporal.workflow_history.helpers import (
    extract_encoded_node_payloads,
    get_encoded_input_from_node_id,
    get_input_from_node_id,
    get_node_data_from_node_id,
    extract_node_payloads,
    get_child_workflow_workflow_id_run_id,
    get_output_from_node_id,
    get_encoded_output_from_node_id,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import NodePayloadData


class WorkflowHistory(BaseModel):
    workflow_id: str = Field(..., description="Unique identifier for the workflow")
    run_id: str = Field(..., description="Unique identifier for the workflow run")
    events: list[dict] = Field(..., description="List of workflow events")

    def get_node_input(self, node_id: str) -> dict | None:
        """
        Get input payload for a specific node ID.

        Args:
            node_id: The node ID to get input for

        Returns:
            Input payload data if found, None otherwise
        """
        return get_input_from_node_id(self.events, node_id)

    def get_node_output(self, node_id: str) -> dict | None:
        """
        Get output payload for a specific node ID.

        Args:
            node_id: The node ID to get output for

        Returns:
            Output payload data if found, None otherwise
        """
        return get_output_from_node_id(self.events, node_id)

    def get_node_data(self, node_id: str) -> dict[str, NodePayloadData]:
        """
        Get all node data (including input/output payloads and all events) for a specific node ID.

        Args:
            node_id: The node ID to get data for

        Returns:
            Dictionary with node_id as key and NodePayloadData as value
        """
        return get_node_data_from_node_id(self.events, node_id)

    def get_nodes_data(self, target_node_ids: list[str] | None = None) -> dict[str, NodePayloadData]:
        """
        Get all node data (including input/output payloads and all events) from the workflow events.

        Args:
            target_node_ids: Optional list of node IDs to filter by

        Returns:
            Dictionary mapping node_id to NodePayloadData
        """
        return extract_node_payloads(self.events, target_node_ids)

    def get_child_workflow_workflow_id_run_id(self, node_id: str) -> tuple[str, str]:
        """
        Get child workflow's workflow_id and run_id from CHILD_WORKFLOW_EXECUTION_STARTED event.

        Args:
            node_id: The node ID of the child workflow (e.g., "ChildWorkflow#1")

        Returns:
            Tuple of (workflow_id, run_id)

        Raises:
            ValueError: If node data is not found or workflow execution details are missing
        """
        return get_child_workflow_workflow_id_run_id(self.events, node_id)

    def get_node_input_encoded(self, node_id: str) -> dict | None:
        """
        Get encoded input payload for a specific node ID.

        Args:
            node_id: The node ID to get encoded input for

        Returns:
            Encoded input payload object (first if multiple exist, with metadata and data) if found, None otherwise
        """
        return get_encoded_input_from_node_id(self.events, node_id)

    def get_node_output_encoded(self, node_id: str) -> dict | None:
        """
        Get encoded output payload for a specific node ID.

        Args:
            node_id: The node ID to get encoded output for

        Returns:
            Encoded output payload object (first if multiple exist, with metadata and data) if found, None otherwise
        """
        return get_encoded_output_from_node_id(self.events, node_id)

    def get_nodes_data_encoded(self, target_node_ids: list[str] | None = None) -> dict[str, NodePayload]:
        """
        Get all encoded node data from the workflow events.

        Args:
            target_node_ids: Optional list of node IDs to filter by

        Returns:
            Dictionary mapping node_id to NodePayload instances with encoded input/output
        """
        return extract_encoded_node_payloads(self.events, target_node_ids)
