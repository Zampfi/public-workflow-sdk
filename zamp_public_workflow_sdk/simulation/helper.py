"""
Helper functions for Temporal History simulation strategy.

These functions can be used by other modules that need to work with Temporal workflow history.
"""

from collections import defaultdict
from typing import Any

import structlog

from zamp_public_workflow_sdk.simulation.constants import PayloadKey
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    WorkflowHistory,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.fetch_temporal_workflow_history import (
    FetchTemporalWorkflowHistoryInput,
    FetchTemporalWorkflowHistoryOutput,
)

logger = structlog.get_logger(__name__)

MAIN_WORKFLOW_IDENTIFIER = "main_workflow"  # Identifier for top-level workflow nodes


async def fetch_temporal_history(
    node_ids: list[str],
    workflow_id: str | None = None,
    run_id: str | None = None,
) -> WorkflowHistory | None:
    """
    Fetch temporal workflow history for a workflow (main or child).

    This function fetches the workflow history from Temporal, which includes all events
    for the specified workflow execution.

    Args:
        node_ids: List of node execution IDs to filter history for
        workflow_id: Optional workflow ID to fetch
        run_id: Optional run ID to fetch

    Returns:
        WorkflowHistory object if successful, None if fetch fails
    """
    from zamp_public_workflow_sdk.actions_hub import ActionsHub

    try:
        workflow_history = await ActionsHub.execute_child_workflow(
            "FetchTemporalWorkflowHistoryWorkflow",
            FetchTemporalWorkflowHistoryInput(
                workflow_id=workflow_id,
                run_id=run_id,
                node_ids=node_ids,
                decode_payloads=False,
            ),
            result_type=FetchTemporalWorkflowHistoryOutput,
        )
        return workflow_history

    except Exception as e:
        logger.error(
            "Failed to fetch temporal history",
            error=str(e),
            error_type=type(e).__name__,
            workflow_id=workflow_id,
            run_id=run_id,
        )
        raise Exception(f"Failed to fetch temporal history for workflow_id={workflow_id}, run_id={run_id}") from e


async def extract_node_payload(
    node_ids: list[str],
    workflow_histories_map: dict[str, WorkflowHistory],
) -> dict[str, dict[str, Any | None]]:
    """
    Extract input and output payloads for specific nodes from temporal history.

    This function handles both main workflow nodes and child workflow nodes.
    For child workflow nodes, it recursively fetches their history and extracts inputs/outputs.

    Args:
        node_ids: List of node execution IDs to extract input/output for
        workflow_histories_map: Dictionary mapping workflow paths to their histories

    Returns:
        Dictionary mapping node IDs to dict with PayloadKey.INPUT_PAYLOAD and PayloadKey.OUTPUT_PAYLOAD keys

    Raises:
        Exception: If node inputs/outputs cannot be extracted
    """
    logger.info("Extracting node outputs", node_ids=node_ids)

    # Group nodes by their immediate parent workflow
    node_groups = group_nodes_by_parent_workflow(node_ids)
    logger.info("Node groups", node_groups=node_groups)
    all_node_outputs = {}

    workflow_nodes_needed = collect_nodes_per_workflow(node_ids=node_ids)
    logger.info("Workflow nodes needed to mock", workflow_nodes_needed=workflow_nodes_needed)
    temporal_history = workflow_histories_map[MAIN_WORKFLOW_IDENTIFIER]

    for parent_workflow_id, workflow_nodes in node_groups.items():
        if parent_workflow_id == MAIN_WORKFLOW_IDENTIFIER:
            # Main workflow nodes - extract directly from current history
            main_workflow_outputs = extract_main_workflow_node_payloads(
                temporal_history=temporal_history, node_ids=workflow_nodes
            )
            logger.info("main workflow outputs", length_of_outputs=len(main_workflow_outputs))
            all_node_outputs.update(main_workflow_outputs)
        else:
            # Child workflow nodes - need to fetch child workflow history
            child_workflow_outputs = await extract_child_workflow_node_payloads(
                parent_history=temporal_history,
                child_workflow_id=parent_workflow_id,
                node_ids=workflow_nodes,
                workflow_nodes_needed=workflow_nodes_needed,
                workflow_histories_map=workflow_histories_map,
            )
            logger.info("child workflow outputs", length_of_outputs=len(child_workflow_outputs))
            all_node_outputs.update(child_workflow_outputs)

    return all_node_outputs


def extract_main_workflow_node_payloads(
    temporal_history: WorkflowHistory, node_ids: list[str]
) -> dict[str, dict[str, Any | None]]:
    """
    Extract encoded input and output payloads for nodes that belong to the main workflow.

    Args:
        temporal_history: The main workflow history object
        node_ids: List of node IDs in the main workflow

    Returns:
        Dictionary mapping node IDs to dict with PayloadKey.INPUT_PAYLOAD, PayloadKey.OUTPUT_PAYLOAD,
        and potentially other metadata keys (e.g., NEEDS_CHILD_TRAVERSAL)
    """
    # Get the full encoded payloads including all metadata (like NEEDS_CHILD_TRAVERSAL)
    return temporal_history.get_nodes_data_encoded(target_node_ids=node_ids)


async def extract_child_workflow_node_payloads(
    parent_history: WorkflowHistory,
    child_workflow_id: str,
    node_ids: list[str],
    workflow_nodes_needed: dict[str, list[str]] | None,
    workflow_histories_map: dict[str, WorkflowHistory],
) -> dict[str, dict[str, Any | None]]:
    """
    Extract input and output payloads for nodes that belong to a child workflow.

    This function:
    1. Gets child workflow's workflow_id and run_id from parent's history
    2. Fetches the child workflow's history (or reuses cached)
    3. Extracts node input and output payloads from child workflow history

    Args:
        parent_history: The parent workflow history object
        child_workflow_id: The child workflow identifier (e.g., "ChildWorkflow#1")
        node_ids: List of node IDs in the child workflow
        workflow_nodes_needed: Pre-collected map of workflow paths to their needed nodes
        workflow_histories_map: Dictionary mapping workflow paths to their histories

    Returns:
        Dictionary mapping node IDs to dict with PayloadKey.INPUT_PAYLOAD and PayloadKey.OUTPUT_PAYLOAD keys (None if not found)
    """
    if workflow_nodes_needed is None:
        workflow_nodes_needed = {}

    # Extract the full path to the child workflow by finding where it appears in the node ID
    # Given a node like "Parent#1.Child#1.activity#1" and child_workflow_id "Child#1",
    # this returns "Parent#1.Child#1" (the path up to and including the child workflow)
    full_child_path = get_workflow_path_from_node(node_id=node_ids[0], child_workflow_id=child_workflow_id)
    logger.info("full child path", full_child_path=full_child_path)

    # Fetch child workflow history (traverses nested paths if needed)
    child_history = await fetch_nested_child_workflow_history(
        parent_workflow_history=parent_history,
        full_child_path=full_child_path,
        node_ids=node_ids,
        workflow_nodes_needed=workflow_nodes_needed,
        workflow_histories_map=workflow_histories_map,
    )
    logger.info(
        "Child history present with workflow_id and run_id",
        run_id=child_history.run_id,
        workflow_id=child_history.workflow_id,
    )
    if not child_history:
        raise Exception(
            f"Failed to fetch child workflow history for child_node_id={full_child_path}, "
            f"child_workflow_id={child_workflow_id}, node_ids={node_ids}"
        )

    # Extract encoded inputs and outputs using full node IDs (workflow stores with prefix, e.g., "Parent#1.activity#1")
    child_nodes_data = child_history.get_nodes_data_encoded()
    node_outputs = {}

    for full_node_id in node_ids:
        if full_node_id in child_nodes_data:
            node_outputs[full_node_id] = {
                PayloadKey.INPUT_PAYLOAD: child_nodes_data[full_node_id].get(PayloadKey.INPUT_PAYLOAD),
                PayloadKey.OUTPUT_PAYLOAD: child_nodes_data[full_node_id].get(PayloadKey.OUTPUT_PAYLOAD),
            }
        else:
            node_outputs[full_node_id] = {
                PayloadKey.INPUT_PAYLOAD: None,
                PayloadKey.OUTPUT_PAYLOAD: None,
            }

    return node_outputs


async def fetch_nested_child_workflow_history(
    parent_workflow_history: WorkflowHistory,
    full_child_path: str,
    node_ids: list[str],
    workflow_nodes_needed: dict[str, list[str]] | None,
    workflow_histories_map: dict[str, WorkflowHistory],
) -> WorkflowHistory | None:
    """
    Fetch nested child workflow by traversing the path.
    E.g., "Parent#1.Child#1" fetches Parent#1, then Child#1 from Parent#1.

    Args:
        parent_workflow_history: The parent workflow history object
        full_child_path: Full path to the child workflow (e.g., "Parent#1.Child#1")
        node_ids: List of node IDs to fetch
        workflow_histories_map: Dictionary mapping workflow paths to their histories (will be updated)
        workflow_nodes_needed: Pre-collected map of workflow paths to their needed nodes

    Returns:
        WorkflowHistory object for the child workflow, or None if fetch fails
    """
    if workflow_nodes_needed is None:
        workflow_nodes_needed = {}

    path_parts = full_child_path.split(".")
    current_history = parent_workflow_history

    for depth_level in range(len(path_parts)):
        current_path = ".".join(path_parts[: depth_level + 1])

        if current_path in workflow_histories_map:
            current_history = workflow_histories_map[current_path]
            logger.info("Using cached history", current_path=current_path)
            continue

        # Get workflow_id and run_id from parent using full prefixed node_id
        try:
            workflow_id_run_id = current_history.get_child_workflow_workflow_id_run_id(node_id=current_path)
            workflow_id, run_id = workflow_id_run_id
        except ValueError as e:
            raise Exception(
                f"Failed to get workflow_id and run_id for child workflow at path={current_path}. "
                f"Child workflow execution may not have started or node_id may be invalid. "
                f"Original error: {str(e)}"
            ) from e

        # Use pre-collected nodes
        if current_path in workflow_nodes_needed:
            fetch_node_ids = workflow_nodes_needed[current_path]
        else:
            is_final_level = depth_level == len(path_parts) - 1
            if is_final_level:
                # Final level: fetch the actual nodes with full prefix
                fetch_node_ids = node_ids
            else:
                # Intermediate level: fetch the next child workflow with prefix
                fetch_node_ids = [".".join(path_parts[: depth_level + 2])]

        # Fetch and cache
        current_history = await fetch_temporal_history(
            node_ids=fetch_node_ids,
            workflow_id=workflow_id,
            run_id=run_id,
        )
        if not current_history:
            return None

        workflow_histories_map[current_path] = current_history

    return current_history


def get_workflow_path_from_node(node_id: str, child_workflow_id: str) -> str:
    """
    Extract workflow path up to child_workflow_id from a node_id.

    This finds where the child_workflow_id appears in the node_id path and returns
    everything up to and including it.

    Examples:
        - node_id="Parent#1.Child#1.activity#1", child_workflow_id="Child#1"
          -> "Parent#1.Child#1"
        - node_id="Parent#1.Child#1.GrandChild#1.task#1", child_workflow_id="GrandChild#1"
          -> "Parent#1.Child#1.GrandChild#1"
        - node_id="Child#1.activity#1", child_workflow_id="Child#1"
          -> "Child#1"
        - node_id="activity#1", child_workflow_id="Parent#1" (not found)
          -> "Parent#1" (returns the child_workflow_id itself as fallback)
    """
    parts = node_id.split(".")
    try:
        child_index = parts.index(child_workflow_id)
        return ".".join(parts[: child_index + 1])
    except ValueError:
        logger.error(
            "Child workflow ID not found in node path",
            node_id=node_id,
            child_workflow_id=child_workflow_id,
        )
        return child_workflow_id


def collect_nodes_per_workflow(node_ids: list[str]) -> dict[str, list[str]]:
    """
    Collect all node_ids needed from each workflow for batching (with workflow prefix).

    Input: ["Parent#1.query#1", "Parent#1.Child#1.activity#1"]
    Output: {"Parent#1": ["Parent#1.query#1", "Parent#1.Child#1"],
             "Parent#1.Child#1": ["Parent#1.Child#1.activity#1"]}
    """
    workflow_nodes = {}

    for node_id in node_ids:
        parts = node_id.split(".")

        # For each level, collect what that workflow needs (with prefix)
        for depth_level in range(1, len(parts)):
            workflow_path = ".".join(parts[:depth_level])
            node_with_prefix = ".".join(parts[: depth_level + 1])

            # Initialize workflow path if not seen before
            if workflow_path not in workflow_nodes:
                workflow_nodes[workflow_path] = []

            # Skip if this node
            if node_with_prefix in workflow_nodes[workflow_path]:
                continue

            workflow_nodes[workflow_path].append(node_with_prefix)

    return workflow_nodes


def group_nodes_by_parent_workflow(node_ids: list[str]) -> dict[str, list[str]]:
    """
    Group node IDs by their immediate parent workflow using full path.
    - 'activity#1' -> parent = MAIN_WORKFLOW_IDENTIFIER
    - 'Child#1.activity#1' -> parent = 'Child#1'
    - 'Parent#1.Child#1.activity#1' -> parent = 'Parent#1.Child#1'
    - 'A#1.B#1.C#1.activity#1' -> parent = 'A#1.B#1.C#1'

    This ensures that multiple instances of the same workflow name in different
    parts of the hierarchy are grouped separately.
    """
    node_groups = defaultdict(list)

    for node_id in node_ids:
        parts = node_id.split(".")

        if len(parts) == 1:
            parent = MAIN_WORKFLOW_IDENTIFIER
        else:
            # Use full path up to (but not including) the last part
            parent = ".".join(parts[:-1])

        node_groups[parent].append(node_id)

    return node_groups
