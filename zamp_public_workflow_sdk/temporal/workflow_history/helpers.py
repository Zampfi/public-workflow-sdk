"""
Helper functions for temporal workflow history operations.
"""

import structlog

from zamp_public_workflow_sdk.simulation.constants import (
    PayloadKey,
)
from zamp_public_workflow_sdk.simulation.models.node_payload import NodePayload
from zamp_public_workflow_sdk.temporal.workflow_history.constants import (
    EventField,
    EventType,
    EventTypeToAttributesKey,
    PayloadField,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import (
    NodePayloadData,
)
from zamp_public_workflow_sdk.temporal.workflow_history.constants.constants import WorkflowExecutionField

logger = structlog.get_logger(__name__)


def _get_attributes_key_for_event_type(event_type: str) -> str | None:
    """Get the attributes key for a given event type."""
    logger.info("Getting attributes key for event type", event_type=event_type)
    try:
        event_type_enum = EventType(event_type)
        attrs_key_enum = getattr(EventTypeToAttributesKey, event_type_enum.name)
        result = attrs_key_enum.value
        logger.info("Successfully found attributes key", event_type=event_type, attrs_key=result)
        return result
    except (ValueError, AttributeError) as e:
        logger.warning(
            "Failed to get attributes key for event type",
            event_type=event_type,
            error=str(e),
        )
        return None


def _get_node_id_from_header(header_fields: dict) -> str | None:
    """Extract node_id from header fields."""
    logger.info("Extracting node_id from header fields", header_fields=header_fields)
    if EventField.NODE_ID.value not in header_fields:
        logger.info("Node ID field not found in header")
        return None
    node_id_data = header_fields[EventField.NODE_ID.value]
    if isinstance(node_id_data, dict) and PayloadField.DATA.value in node_id_data:
        result = node_id_data[PayloadField.DATA.value]
        logger.info("Successfully extracted node_id from header", node_id=result)
        return result
    logger.info("Node ID data is not in expected format", node_id_data=node_id_data)
    return None


def extract_node_id_from_event(event: dict) -> str | None:
    """Extract node_id from a workflow event."""
    logger.info(
        "Extracting node_id from event",
        event_type=event.get(EventField.EVENT_TYPE.value),
    )

    if PayloadField.HEADER.value in event and PayloadField.FIELDS.value in event[PayloadField.HEADER.value]:
        logger.info("Found header fields in event, extracting node_id")
        node_id = _get_node_id_from_header(event[PayloadField.HEADER.value][PayloadField.FIELDS.value])
        if node_id:
            logger.info("Successfully extracted node_id from event header", node_id=node_id)
            return node_id

    event_type = event.get(EventField.EVENT_TYPE.value)
    attrs_key = _get_attributes_key_for_event_type(event_type)

    if attrs_key and attrs_key in event:
        logger.info("Found attributes key in event, checking for node_id", attrs_key=attrs_key)
        attrs = event[attrs_key]
        if PayloadField.HEADER.value in attrs and PayloadField.FIELDS.value in attrs[PayloadField.HEADER.value]:
            node_id = _get_node_id_from_header(attrs[PayloadField.HEADER.value][PayloadField.FIELDS.value])
            if node_id:
                logger.info(
                    "Successfully extracted node_id from event attributes",
                    node_id=node_id,
                )
                return node_id

    logger.info("No node_id found in event")
    return None


def _extract_payload_data(event: dict, event_type: str, payload_field: str) -> list | None:
    """Extract payload data from event attributes. Returns list of all payloads."""
    logger.info("Extracting payload data", event_type=event_type, payload_field=payload_field)
    attrs_key = _get_attributes_key_for_event_type(event_type)

    if not attrs_key or attrs_key not in event:
        logger.info("No attributes key found or key not in event", attrs_key=attrs_key)
        return None

    payloads = event[attrs_key].get(payload_field, {}).get(PayloadField.PAYLOADS.value, [])
    if not payloads:
        logger.info("No payload data found in event")
        return None

    # Extract data field from each payload
    payload_data_list = []
    for payload in payloads:
        if PayloadField.DATA.value in payload:
            payload_data_list.append(payload[PayloadField.DATA.value])

    if payload_data_list:
        logger.info("Successfully extracted payload data", payload_count=len(payload_data_list))
        return payload_data_list
    return None


def _extract_payload_encoded(event: dict, event_type: str, payload_field: str) -> list | None:
    """
    Extract full encoded payloads (with metadata and data) from event attributes.

    Returns list of all payload objects.
    Returns None if no payloads found.
    """
    logger.info("Extracting encoded payload", event_type=event_type)
    attrs_key = _get_attributes_key_for_event_type(event_type)

    if not attrs_key or attrs_key not in event:
        logger.info("No attributes key found or key not in event", attrs_key=attrs_key)
        return None

    payloads = event[attrs_key].get(payload_field, {}).get(PayloadField.PAYLOADS.value, [])
    if not payloads:
        logger.info("No encoded payload found in event")
        return None

    logger.info("Successfully extracted encoded payloads", payload_count=len(payloads))
    return payloads


def _should_include_node_id(node_id: str, target_node_ids: list[str] | None) -> bool:
    """Check if node_id should be included based on target_node_ids filter."""
    result = not target_node_ids or node_id in target_node_ids
    logger.info(
        "Checking if node_id should be included",
        node_id=node_id,
        target_node_ids=target_node_ids,
        included=result,
    )
    return result


def _process_event_with_input_payload(event: dict, event_type: EventType) -> tuple[str, str] | None:
    """Process event that has input payload and return (node_id, payload_field) or None."""
    logger.info("Processing event", event_type=event_type.value)
    node_id = extract_node_id_from_event(event)
    if node_id:
        logger.info(
            "Successfully extracted node_id",
            event_type=event_type.value,
            node_id=node_id,
        )
        return node_id, PayloadField.INPUT.value
    else:
        logger.warning("Failed to extract node_id from event", event_type=event_type.value)
    return None


def _process_workflow_execution_completed(
    event: dict,
    workflow_node_id: str | None,
) -> tuple[str, str] | None:
    """Process WORKFLOW_EXECUTION_COMPLETED event and return (node_id, payload_field) or None."""
    logger.info(
        "Processing WORKFLOW_EXECUTION_COMPLETED event",
        workflow_node_id=workflow_node_id,
    )

    if not workflow_node_id:
        logger.info("Skipping workflow execution completed - no workflow_node_id")
        return None

    logger.info("Found workflow node_id for execution completed", node_id=workflow_node_id)
    return workflow_node_id, PayloadField.RESULT.value


def _process_event_with_result_payload(
    event: dict,
    event_type: EventType,
    event_id_field: EventField,
    tracking_events: dict[int, str],
) -> tuple[str, str] | None:
    """Process event that has result payload and return (node_id, payload_field) or None."""
    logger.info("Processing event", event_type=event_type.value)
    attrs_key = _get_attributes_key_for_event_type(event_type.value)
    event_id = event.get(attrs_key, {}).get(event_id_field.value)

    if not event_id or event_id not in tracking_events:
        logger.info(
            "Skipping event - no event ID or not in tracking events",
            event_type=event_type.value,
            event_id_field=event_id_field.value,
            event_id=event_id,
            available_events=list(tracking_events.keys()),
        )
        return None

    node_id = tracking_events[event_id]
    logger.info(
        "Found node_id for event",
        event_type=event_type.value,
        node_id=node_id,
        event_id=event_id,
    )
    return node_id, PayloadField.RESULT.value


def _track_event_with_node_id(
    event: dict,
    node_id: str,
    tracking_events: dict[int, str],
) -> None:
    """Track an event with its node_id for later reference."""
    event_id = event.get(EventField.EVENT_ID.value)
    if event_id:
        tracking_events[event_id] = node_id
        logger.info(
            "Added event to tracking",
            event_id=event_id,
            node_id=node_id,
        )


def _add_event_to_node_events(
    node_id: str,
    event: dict,
    event_type: str,
    node_ids: list[str] | None,
    node_payloads: dict[str, NodePayloadData],
) -> None:
    """Add event to node's event list if node_id matches filter."""
    if node_id and _should_include_node_id(node_id, node_ids):
        if node_id not in node_payloads:
            node_payloads[node_id] = NodePayloadData(node_id=node_id, node_events=[])
        node_payloads[node_id].node_events.append(event)
        logger.info(
            "Added event to node",
            node_id=node_id,
            event_type=event_type,
        )


def _add_event_and_payload(
    node_id: str,
    event: dict,
    payload_field: str,
    node_payloads: dict[str, NodePayloadData],
) -> None:
    """Add event to node data and save input/output payload based on payload_field."""
    logger.info(
        "Adding event and payload to node data",
        node_id=node_id,
        payload_field=payload_field,
    )

    if node_id not in node_payloads:
        logger.info("Creating new node data entry", node_id=node_id)
        node_payloads[node_id] = NodePayloadData(node_id=node_id, node_events=[])

    node_payloads[node_id].node_events.append(event)
    logger.info(
        "Added event to node_events list",
        node_id=node_id,
        event_count=len(node_payloads[node_id].node_events),
    )

    payload = _extract_payload_data(event, event.get(EventField.EVENT_TYPE.value), payload_field)
    if not payload:
        logger.info("No payload data found, skipping payload assignment", node_id=node_id)
        return

    if payload_field == PayloadField.INPUT.value:
        node_payloads[node_id].input_payload = payload
        logger.info("Set input payload for node", node_id=node_id)
    else:
        node_payloads[node_id].output_payload = payload
        logger.info("Set output payload for node", node_id=node_id)


def get_input_from_node_id(events: list[dict], node_id: str) -> dict | None:
    """Get input payload for a specific node ID from events."""
    logger.info("Getting input payload for node", node_id=node_id, event_count=len(events))
    node_data = extract_node_payloads(events, [node_id])
    result = node_data[node_id].input_payload if node_id in node_data else None
    logger.info("Retrieved input payload", node_id=node_id, has_input=result is not None)
    return result


def get_output_from_node_id(events: list[dict], node_id: str) -> dict | None:
    """Get output payload for a specific node ID from events."""
    logger.info("Getting output payload for node", node_id=node_id, event_count=len(events))
    node_data = extract_node_payloads(events, [node_id])
    result = node_data[node_id].output_payload if node_id in node_data else None
    logger.info("Retrieved output payload", node_id=node_id, has_output=result is not None)
    return result


def get_node_data_from_node_id(events: list[dict], node_id: str) -> dict[str, NodePayloadData]:
    """Get all node data (including input/output payloads and all events) for a specific node ID from events."""
    logger.info("Getting all node data for node", node_id=node_id, event_count=len(events))
    result = extract_node_payloads(events, [node_id])
    logger.info("Retrieved node data", node_id=node_id, found=node_id in result)
    return result


def _extract_child_workflow_execution_details(event: dict) -> tuple[str | None, str | None]:
    """
    Extract workflow_id and run_id from a CHILD_WORKFLOW_EXECUTION_STARTED event.

    Args:
        event: The workflow event dictionary

    Returns:
        Tuple of (workflow_id, run_id) or (None, None) if not found
    """
    attrs_key = EventTypeToAttributesKey.CHILD_WORKFLOW_EXECUTION_STARTED.value
    attrs = event.get(attrs_key, {})
    workflow_execution = attrs.get(WorkflowExecutionField.WORKFLOW_EXECUTION.value, {})
    child_workflow_id = workflow_execution.get(WorkflowExecutionField.WORKFLOW_ID.value)
    child_run_id = workflow_execution.get(WorkflowExecutionField.RUN_ID.value)
    return child_workflow_id, child_run_id


def _mark_child_workflows_needing_traversal(
    child_workflow_initiated_events: dict[int, str],
    child_workflow_execution_details: dict[str, tuple[str, str]],
    node_payloads: dict,
    node_ids: list[str] | None,
) -> None:
    """
    Mark child workflows that were initiated but have no output as needing traversal.

    Args:
        child_workflow_initiated_events: Map of event IDs to child node IDs for initiated workflows
        child_workflow_execution_details: Map of node IDs to (workflow_id, run_id) tuples
        node_payloads: Dictionary of node payloads to update
        node_ids: Optional list of node IDs to filter by
    """
    for event_id, child_node_id in child_workflow_initiated_events.items():
        # Skip if not in target nodes
        if not _should_include_node_id(child_node_id, node_ids):
            continue

        # Skip if node not in payloads
        if child_node_id not in node_payloads:
            continue

        # Skip if already has output
        if PayloadKey.OUTPUT_PAYLOAD in node_payloads[child_node_id]:
            continue

        # Get child workflow execution details if available
        if child_node_id not in child_workflow_execution_details:
            logger.warning(
                "Child workflow initiated but no execution details found",
                node_id=child_node_id,
                event_id=event_id,
            )
            continue

        workflow_id, run_id = child_workflow_execution_details[child_node_id]
        logger.info(
            "Child workflow initiated but no output found, will be handled by traversal logic",
            node_id=child_node_id,
            event_id=event_id,
            workflow_id=workflow_id,
            run_id=run_id,
        )


def _process_events_for_payloads(
    events: list[dict],
    node_ids: list[str] | None,
    return_encoded_format: bool = False,
) -> dict:
    """
    logic to process events and extract node_id and payload_field information.

    Args:
        events: List of workflow events
        node_ids: Optional list of node IDs to filter by
        return_encoded_format: If True, returns full encoded payload structure (with metadata and data).
                               If False, returns decoded payload data only.

    Returns:
        Dictionary mapping node_id to payload data (format depends on return_encoded_format)
    """
    node_payloads: dict = {}
    activity_scheduled_events: dict[int, str] = {}
    child_workflow_initiated_events: dict[int, str] = {}
    child_workflow_execution_details: dict[str, tuple[str, str]] = {}  # Maps node_id to (workflow_id, run_id)
    workflow_node_id: str | None = None

    for event_index, event in enumerate(events):
        event_type = event.get(EventField.EVENT_TYPE.value)
        node_id = None
        payload_field = None
        logger.info(
            "Processing event",
            event_index=event_index,
            event_type=event_type,
        )

        # Handle workflow execution started
        if event_type == EventType.WORKFLOW_EXECUTION_STARTED.value:
            result = _process_event_with_input_payload(event, EventType.WORKFLOW_EXECUTION_STARTED)
            if not result:
                continue
            node_id, payload_field = result
            workflow_node_id = node_id

        # Handle child workflow execution started
        if event_type == EventType.CHILD_WORKFLOW_EXECUTION_STARTED.value:
            extracted_node_id = extract_node_id_from_event(event)
            if return_encoded_format:
                if _should_include_node_id(extracted_node_id, node_ids):
                    if extracted_node_id not in node_payloads:
                        node_payloads[extracted_node_id] = NodePayload(node_id=extracted_node_id)
                    # Extract and store workflow_id and run_id from this event
                    child_workflow_id, child_run_id = _extract_child_workflow_execution_details(event)
                    if child_workflow_id and child_run_id:
                        child_workflow_execution_details[extracted_node_id] = (child_workflow_id, child_run_id)
                        logger.info(
                            "Stored child workflow execution details",
                            node_id=extracted_node_id,
                            workflow_id=child_workflow_id,
                            run_id=child_run_id,
                        )
            else:
                _add_event_to_node_events(extracted_node_id, event, event_type, node_ids, node_payloads)
            continue

        # Handle workflow execution completed
        if event_type == EventType.WORKFLOW_EXECUTION_COMPLETED.value:
            if return_encoded_format:
                if workflow_node_id and _should_include_node_id(workflow_node_id, node_ids):
                    node_id = workflow_node_id
                    payload_field = PayloadField.RESULT.value
            else:
                result = _process_workflow_execution_completed(event, workflow_node_id)
                if not result:
                    continue
                node_id, payload_field = result

        # Handle activity task scheduled
        if event_type == EventType.ACTIVITY_TASK_SCHEDULED.value:
            result = _process_event_with_input_payload(event, EventType.ACTIVITY_TASK_SCHEDULED)
            if not result:
                continue
            node_id, payload_field = result
            _track_event_with_node_id(event, node_id, activity_scheduled_events)

        # Handle activity task completed
        if event_type == EventType.ACTIVITY_TASK_COMPLETED.value:
            result = _process_event_with_result_payload(
                event,
                EventType.ACTIVITY_TASK_COMPLETED,
                EventField.SCHEDULED_EVENT_ID,
                activity_scheduled_events,
            )
            if not result:
                continue
            node_id, payload_field = result

        # Handle child workflow execution initiated
        if event_type == EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED.value:
            result = _process_event_with_input_payload(
                event,
                EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED,
            )
            if not result:
                continue
            node_id, payload_field = result
            _track_event_with_node_id(event, node_id, child_workflow_initiated_events)

        # Handle child workflow execution completed
        if event_type == EventType.CHILD_WORKFLOW_EXECUTION_COMPLETED.value:
            result = _process_event_with_result_payload(
                event,
                EventType.CHILD_WORKFLOW_EXECUTION_COMPLETED,
                EventField.INITIATED_EVENT_ID,
                child_workflow_initiated_events,
            )
            if not result:
                continue
            node_id, payload_field = result

        # Skip if we didn't extract a node_id for this event
        if not node_id or not payload_field:
            continue

        # Skip if node_id is not in target list
        if not _should_include_node_id(node_id, node_ids):
            continue

        # Store payload based on format
        if return_encoded_format:
            if node_id not in node_payloads:
                node_payloads[node_id] = NodePayload(node_id=node_id)
            payload = _extract_payload_encoded(event, event_type, payload_field)
            if not payload:
                continue
            if payload_field == PayloadField.INPUT.value:
                node_payloads[node_id].input_payload = payload
            else:
                node_payloads[node_id].output_payload = payload
        else:
            _add_event_and_payload(node_id, event, payload_field, node_payloads)

    # Mark child workflows that were initiated but don't have output (need traversal)
    _mark_child_workflows_needing_traversal(
        child_workflow_initiated_events,
        child_workflow_execution_details,
        node_payloads,
        node_ids,
    )

    return node_payloads


def extract_node_payloads(events: list[dict], node_ids: list[str] | None = None) -> dict[str, NodePayloadData]:
    """Extract all node data including input/output payloads and all events for each node_id from workflow events."""
    logger.info(
        "Starting extraction of all node payloads",
        event_count=len(events),
        target_node_ids=node_ids,
    )

    node_payloads = _process_events_for_payloads(events, node_ids, return_encoded_format=False)

    logger.info(
        "Completed extraction of all node payloads",
        total_nodes=len(node_payloads),
        node_ids=list(node_payloads.keys()),
    )
    return node_payloads


def get_encoded_input_from_node_id(events: list[dict], node_id: str) -> dict | None:
    """Get encoded input payload for a specific node ID. Returns the encoded input payload."""
    logger.info("Getting encoded input payload for node", node_id=node_id)
    node_data = extract_encoded_node_payloads(events, [node_id])
    if node_id not in node_data:
        return None
    node_payload = node_data[node_id]
    return node_payload.input_payload


def get_encoded_output_from_node_id(events: list[dict], node_id: str) -> dict | None:
    """Get encoded output payload for a specific node ID. Returns the encoded output payload."""
    logger.info("Getting encoded output payload for node", node_id=node_id)
    node_data = extract_encoded_node_payloads(events, [node_id])
    if node_id not in node_data:
        return None
    node_payload = node_data[node_id]
    return node_payload.output_payload


def extract_encoded_node_payloads(events: list[dict], node_ids: list[str] | None = None) -> dict[str, NodePayload]:
    """Extract all encoded node data from workflow events."""
    logger.info("Extracting encoded node payloads", event_count=len(events), target_node_ids=node_ids)

    node_payloads = _process_events_for_payloads(events, node_ids, return_encoded_format=True)

    logger.info("Completed extraction of encoded node payloads", total_nodes=len(node_payloads))
    return node_payloads


def get_child_workflow_workflow_id_run_id(events: list[dict], node_id: str) -> tuple[str, str]:
    """
    Get child workflow's workflow_id and run_id from CHILD_WORKFLOW_EXECUTION_STARTED event.

    Args:
        events: List of workflow events
        node_id: The node ID of the child workflow (e.g., "ChildWorkflow#1")

    Returns:
        Tuple of (workflow_id, run_id)

    Raises:
        ValueError: If node data is not found or workflow execution details are missing
    """
    logger.info(
        "Getting child workflow workflow_id and run_id",
        node_id=node_id,
        event_count=len(events),
    )

    # Get node data for the specified child workflow
    node_data = get_node_data_from_node_id(events, node_id)
    if not node_data or node_id not in node_data:
        logger.error("No node data found for child workflow", node_id=node_id)
        raise ValueError(
            f"No node data found for child workflow with node_id={node_id}. "
            f"The child workflow may not have been executed or the node_id is invalid."
        )

    node_payload_data = node_data[node_id]

    # Find the CHILD_WORKFLOW_EXECUTION_STARTED event which contains workflow_id and run_id
    for event in node_payload_data.node_events:
        event_type = event.get(EventField.EVENT_TYPE.value)

        if event_type != EventType.CHILD_WORKFLOW_EXECUTION_STARTED.value:
            continue

        # Extract attributes from the event
        attrs_key = EventTypeToAttributesKey.CHILD_WORKFLOW_EXECUTION_STARTED.value
        attrs = event.get(attrs_key)
        if not attrs:
            continue

        # Extract workflow execution details
        workflow_execution = attrs.get(WorkflowExecutionField.WORKFLOW_EXECUTION.value, {})
        child_workflow_id = workflow_execution.get(WorkflowExecutionField.WORKFLOW_ID.value)
        child_run_id = workflow_execution.get(WorkflowExecutionField.RUN_ID.value)

        # Validate both IDs are present before returning
        if child_workflow_id and child_run_id:
            return (child_workflow_id, child_run_id)

    logger.error("No child workflow workflow_id and run_id found in events", node_id=node_id)
    raise ValueError(
        f"No child workflow workflow_id and run_id found for node_id={node_id}. "
        f"The CHILD_WORKFLOW_EXECUTION_STARTED event may be missing or incomplete."
    )
