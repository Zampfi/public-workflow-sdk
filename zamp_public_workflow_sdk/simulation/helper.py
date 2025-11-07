"""
Helper functions for Temporal History simulation strategy.

These functions can be used by other modules that need to work with Temporal workflow history.
"""

from collections import defaultdict

import structlog

from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload
from zamp_public_workflow_sdk.simulation.models.node_payload_models import (
    NodePayloadResult,
    NodePayloadType,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    WorkflowHistory,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.fetch_temporal_workflow_history import (
    FetchTemporalWorkflowHistoryInput,
    FetchTemporalWorkflowHistoryOutput,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import (
    DecodeNodePayloadInput,
    DecodeNodePayloadOutput,
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
) -> dict[str, NodePayload]:
    """
    Extract input and output payloads for specific nodes from temporal history.

    This function handles both main workflow nodes and child workflow nodes.
    For child workflow nodes, it recursively fetches their history and extracts inputs/outputs.
    It also handles child workflow traversal for nodes that need it (when child workflows
    are started but not completed in the parent history).

    Args:
        node_ids: List of node execution IDs to extract input/output for
        workflow_histories_map: Dictionary mapping workflow paths to their histories

    Returns:
        Dictionary mapping node IDs to NodePayload instances with input_payload and output_payload

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

    all_node_outputs = await handle_child_workflow_traversal(
        node_payloads=all_node_outputs,
        main_workflow_history=temporal_history,
    )

    return all_node_outputs


def extract_main_workflow_node_payloads(
    temporal_history: WorkflowHistory, node_ids: list[str]
) -> dict[str, NodePayload]:
    """
    Extract encoded input and output payloads for nodes that belong to the main workflow.

    Args:
        temporal_history: The main workflow history object
        node_ids: List of node IDs in the main workflow

    Returns:
        Dictionary mapping node IDs to NodePayload instances with input_payload and output_payload
    """
    nodes_data = temporal_history.get_nodes_data_encoded(target_node_ids=node_ids)
    return nodes_data


async def extract_child_workflow_node_payloads(
    parent_history: WorkflowHistory,
    child_workflow_id: str,
    node_ids: list[str],
    workflow_nodes_needed: dict[str, list[str]] | None,
    workflow_histories_map: dict[str, WorkflowHistory],
) -> dict[str, NodePayload]:
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
        Dictionary mapping node IDs to NodePayload instances with input_payload and output_payload
    """
    if workflow_nodes_needed is None:
        workflow_nodes_needed = {}

    # Extract the full path to the child workflow by finding where it appears in the node ID
    # Given a node like "Parent#1.Child#1.activity#1" and child_workflow_id "Child#1",
    # this returns "Parent#1.Child#1" (the path up to and including the child workflow)
    full_child_path = get_workflow_path_from_node(node_id=node_ids[0], child_workflow_id=child_workflow_id)
    logger.info("Child workflow node_id", full_child_path=full_child_path)

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
            payload = child_nodes_data[full_node_id]
            payload.node_id = full_node_id
            node_outputs[full_node_id] = payload
        else:
            node_outputs[full_node_id] = NodePayload(
                node_id=full_node_id,
                input_payload=None,
                output_payload=None,
            )

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


async def handle_child_workflow_traversal(
    node_payloads: dict[str, NodePayload],
    main_workflow_history: WorkflowHistory,
) -> dict[str, NodePayload]:
    """
    Handle child workflow traversal for nodes that need it.

    This function checks if any nodes need child workflow traversal (when child workflows
    are started but not completed in the parent history) and fetches the actual outputs
    from the child workflow history.

    Args:
        node_payloads: Dictionary mapping node IDs to NodePayload instances
        main_workflow_history: The main workflow history to check for child workflow details

    Returns:
        Updated dictionary with child workflow outputs where needed
    """
    payloads = {}

    for node_id, payload in node_payloads.items():
        if not needs_child_workflow_traversal(payload, main_workflow_history, node_id):
            payloads[node_id] = payload
            continue

        try:
            child_workflow_id, child_run_id = main_workflow_history.get_child_workflow_workflow_id_run_id(
                node_id=node_id
            )

            logger.info(
                "Traversing child workflow",
                node_id=node_id,
                child_workflow_id=child_workflow_id,
                child_run_id=child_run_id,
            )

            child_payload = await traverse_child_workflow_for_payload(
                node_id=node_id,
                child_workflow_id=child_workflow_id,
                child_run_id=child_run_id,
            )

            if not child_payload:
                payloads[node_id] = payload
                logger.warning("No main workflow node found in child history", node_id=node_id)
                continue

            payloads[node_id] = child_payload
            logger.info("Successfully extracted child workflow output", node_id=node_id)

        except Exception as e:
            logger.error(
                "Failed to traverse child workflow",
                node_id=node_id,
                error=str(e),
            )
            payloads[node_id] = payload

    return payloads


def needs_child_workflow_traversal(
    payload: NodePayload,
    main_workflow_history: WorkflowHistory,
    node_id: str,
) -> bool:
    """
    Check if a node payload needs child workflow traversal.

    A node needs traversal if:
    1. It has no output payload (indicating child workflow didn't complete in parent)
    2. The main workflow history has child workflow workflow_id and run_id for this node

    Args:
        payload: The NodePayload to check
        main_workflow_history: The main workflow history
        node_id: The node ID to check

    Returns:
        True if child workflow traversal is needed, False otherwise
    """
    if payload.output_payload is not None:
        return False

    try:
        child_workflow_id, child_run_id = main_workflow_history.get_child_workflow_workflow_id_run_id(node_id=node_id)
        return child_workflow_id is not None and child_run_id is not None
    except (ValueError, Exception):
        return False


async def traverse_child_workflow_for_payload(
    node_id: str,
    child_workflow_id: str,
    child_run_id: str,
) -> NodePayload | None:
    """
    Traverse into child workflow and return the main workflow node payload.

    Args:
        node_id: The parent node ID
        child_workflow_id: The child workflow ID
        child_run_id: The child workflow run ID

    Returns:
        The child workflow's main node NodePayload if found, otherwise None
    """
    try:
        # Fetch child workflow history
        child_history = await fetch_temporal_history(
            node_ids=[node_id],
            workflow_id=child_workflow_id,
            run_id=child_run_id,
        )

        if not child_history:
            return None

        child_payloads = child_history.get_nodes_data_encoded(target_node_ids=None)
        logger.info(
            "Child workflow payloads extracted",
            node_id=node_id,
            child_payloads_count=len(child_payloads),
        )
        child_main_node = find_main_workflow_node(child_payloads=child_payloads, node_id=node_id)
        return child_main_node

    except Exception as e:
        logger.error(
            "Failed to fetch child workflow history",
            node_id=node_id,
            child_workflow_id=child_workflow_id,
            child_run_id=child_run_id,
            error=str(e),
        )
        return None


def find_main_workflow_node(child_payloads: dict[str, NodePayload], node_id: str) -> NodePayload | None:
    """
    Find the main workflow node in child payloads.

    The main workflow node is the full workflow path that contains the activity.
    This is everything before the last segment (the activity name).

    Examples:
        - node_id="EnhancedStripeInvoiceProcessingWorkflow#1.query_data#1"
          -> extracts "EnhancedStripeInvoiceProcessingWorkflow#1" and searches for it in child_payloads
        - node_id="EnhancedStripeInvoiceProcessingWorkflow#1.POBackedInvoiceProcessingWorkflow#1.emit_custom_log#1"
          -> extracts "EnhancedStripeInvoiceProcessingWorkflow#1.POBackedInvoiceProcessingWorkflow#1" and searches for it in child_payloads
        - node_id="Parent#1.Child#1.GrandChild#1.activity#1"
          -> extracts "Parent#1.Child#1.GrandChild#1" and searches for it in child_payloads

    Args:
        child_payloads: Dictionary mapping node IDs to NodePayload instances
        node_id: Node ID (full path including activity)

    Returns:
        The main workflow NodePayload or None if not found
    """
    parts = node_id.split(".")
    target_workflow_path = ".".join(parts[:-1]) if len(parts) > 1 else parts[0]

    if target_workflow_path in child_payloads:
        return child_payloads[target_workflow_path]

    for child_node_id, child_payload in child_payloads.items():
        if child_node_id.startswith(target_workflow_path + "."):
            return child_payload

    return None


def payload_needs_decoding(payload_item):
    """Check if a payload dict needs decoding."""
    return isinstance(payload_item, dict) and payload_item.get("metadata", {}).get("encoding") is not None


async def build_node_payload(
    workflow_id: str,
    run_id: str,
    output_config: dict[str, NodePayloadType],
) -> list[NodePayloadResult]:
    """
    Build node payload results from workflow history based on output_config.

    This is a unified method that can be called from any workflow to extract and decode
    node payloads from a workflow execution. It orchestrates:
    1. Fetching temporal workflow history
    2. Extracting encoded node payloads from history
    3. Decode payload and build NodePayloadResult objects

    Args:
        workflow_id: The workflow ID to fetch history for
        run_id: The run ID to fetch history for
        output_config: Dictionary mapping node IDs to payload types (INPUT, OUTPUT, INPUT_OUTPUT)

    Returns:
        List of NodePayloadResult objects with decoded input/output based on payload types

    Raises:
        Exception: If fetching history or extracting payloads fails

    Example:
        output_config = {
            "gmail_search_messages#1": NodePayloadType.INPUT_OUTPUT,
            "parse_email#3": NodePayloadType.OUTPUT
        }
        results = await build_node_payload(
            workflow_id="wf-123",
            run_id="run-456",
            output_config=output_config
        )
    """
    logger.info(
        "Building node payload results",
        workflow_id=workflow_id,
        run_id=run_id,
        node_count=len(output_config),
    )

    node_ids = list(output_config.keys())

    temporal_history = await fetch_temporal_history(
        node_ids=node_ids,
        workflow_id=workflow_id,
        run_id=run_id,
    )

    if not temporal_history:
        raise Exception(f"Failed to fetch temporal history for workflow_id={workflow_id}, run_id={run_id}")

    encoded_node_payloads = await extract_node_payload(
        node_ids=node_ids,
        workflow_histories_map={MAIN_WORKFLOW_IDENTIFIER: temporal_history},
    )

    logger.info(
        "Extracted encoded node payloads",
        workflow_id=workflow_id,
        extracted_count=len(encoded_node_payloads),
    )

    node_payload_results = await _decode_and_build_results(
        encoded_node_payloads=encoded_node_payloads,
        output_config=output_config,
        workflow_id=workflow_id,
    )

    logger.info(
        "Successfully built node payload results",
        workflow_id=workflow_id,
        run_id=run_id,
        result_count=len(node_payload_results),
    )

    return node_payload_results


async def _decode_and_build_results(
    encoded_node_payloads: dict[str, NodePayload],
    output_config: dict[str, NodePayloadType],
    workflow_id: str,
) -> list[NodePayloadResult]:
    """
    Decode encoded payloads and build NodePayloadResult objects.

    This function decodes encoded payloads and constructs NodePayloadResult objects
    based on the output_config specification.

    Args:
        encoded_node_payloads: Dictionary mapping node IDs to encoded NodePayload instances
        output_config: Dictionary mapping node IDs to payload types (INPUT, OUTPUT, INPUT_OUTPUT)
        workflow_id: Workflow ID for logging purposes

    Returns:
        List of NodePayloadResult objects with decoded input/output
    """
    node_payload_results: list[NodePayloadResult] = []

    for node_id, payload_type in output_config.items():
        encoded_payload = encoded_node_payloads.get(node_id)

        if not encoded_payload:
            logger.warning(
                "No encoded payload found for node",
                node_id=node_id,
                workflow_id=workflow_id,
            )
            continue

        decoded_data = await _decode_node_payload(
            node_id=node_id,
            encoded_payload=encoded_payload,
            payload_type=payload_type,
        )

        if not decoded_data:
            logger.warning(
                "Failed to decode payload for node",
                node_id=node_id,
                workflow_id=workflow_id,
            )
            continue

        decoded_input = None
        decoded_output = None

        if payload_type in [NodePayloadType.INPUT, NodePayloadType.INPUT_OUTPUT]:
            decoded_input = decoded_data.decoded_input

        if payload_type in [NodePayloadType.OUTPUT, NodePayloadType.INPUT_OUTPUT]:
            decoded_output = decoded_data.decoded_output

        node_payload_results.append(
            NodePayloadResult(
                node_id=node_id,
                input=decoded_input,
                output=decoded_output,
            )
        )

    return node_payload_results


async def _decode_node_payload(
    node_id: str,
    encoded_payload: NodePayload,
    payload_type: NodePayloadType,
) -> DecodeNodePayloadOutput | None:
    """
    Decode node payload using decode_node_payload activity.

    Args:
        node_id: The node ID
        encoded_payload: NodePayload instance with encoded data
        payload_type: The payload type (INPUT, OUTPUT, or INPUT_OUTPUT)

    Returns:
        Decoded payload result or None if decoding fails
    """
    from zamp_public_workflow_sdk.actions_hub import ActionsHub

    try:
        input_to_decode = None
        output_to_decode = None

        if payload_type in [NodePayloadType.INPUT, NodePayloadType.INPUT_OUTPUT]:
            input_to_decode = encoded_payload.input_payload

        if payload_type in [NodePayloadType.OUTPUT, NodePayloadType.INPUT_OUTPUT]:
            output_to_decode = encoded_payload.output_payload

        decoded_data = await ActionsHub.execute_activity(
            "decode_node_payload",
            DecodeNodePayloadInput(
                node_id=node_id,
                input_payload=input_to_decode,
                output_payload=output_to_decode,
            ),
            summary=f"{node_id}",
            return_type=DecodeNodePayloadOutput,
        )

        logger.info(
            "Successfully decoded node payload",
            node_id=node_id,
            payload_type=payload_type.value,
            has_input=decoded_data.decoded_input is not None,
            has_output=decoded_data.decoded_output is not None,
        )

        return decoded_data

    except Exception as e:
        logger.error(
            "Failed to decode node payload",
            node_id=node_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None
