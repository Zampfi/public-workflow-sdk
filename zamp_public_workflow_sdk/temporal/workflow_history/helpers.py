"""
Helper functions for temporal workflow history operations.
"""

import base64
import structlog
from typing import List, Optional, Dict

from zamp_public_workflow_sdk.temporal.workflow_history.constants import (
    EventType,
    PayloadField,
    EventTypeToAttributesKey,
    EventField,
)

from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import (
    NodePayloadData,
)

logger = structlog.get_logger(__name__)


def _get_attributes_key_for_event_type(event_type: str) -> Optional[str]:
    """Get the attributes key for a given event type."""
    logger.info("Getting attributes key for event type", event_type=event_type)
    try:
        event_type_enum = EventType(event_type)
        attrs_key_enum = getattr(EventTypeToAttributesKey, event_type_enum.name)
        result = attrs_key_enum.value
        logger.info(
            "Successfully found attributes key", event_type=event_type, attrs_key=result
        )
        return result
    except (ValueError, AttributeError) as e:
        logger.warning(
            "Failed to get attributes key for event type",
            event_type=event_type,
            error=str(e),
        )
        return None


def _get_node_id_from_header(header_fields: dict) -> Optional[str]:
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


def extract_node_id_from_event(event: dict) -> Optional[str]:
    """Extract node_id from a workflow event."""
    logger.info(
        "Extracting node_id from event",
        event_type=event.get(EventField.EVENT_TYPE.value),
    )

    if (
        PayloadField.HEADER.value in event
        and PayloadField.FIELDS.value in event[PayloadField.HEADER.value]
    ):
        logger.info("Found header fields in event, extracting node_id")
        node_id = _get_node_id_from_header(
            event[PayloadField.HEADER.value][PayloadField.FIELDS.value]
        )
        if node_id:
            logger.info(
                "Successfully extracted node_id from event header", node_id=node_id
            )
            return node_id

    event_type = event.get(EventField.EVENT_TYPE.value)
    attrs_key = _get_attributes_key_for_event_type(event_type)

    if attrs_key and attrs_key in event:
        logger.info(
            "Found attributes key in event, checking for node_id", attrs_key=attrs_key
        )
        attrs = event[attrs_key]
        if (
            PayloadField.HEADER.value in attrs
            and PayloadField.FIELDS.value in attrs[PayloadField.HEADER.value]
        ):
            node_id = _get_node_id_from_header(
                attrs[PayloadField.HEADER.value][PayloadField.FIELDS.value]
            )
            if node_id:
                logger.info(
                    "Successfully extracted node_id from event attributes",
                    node_id=node_id,
                )
                return node_id

    logger.info("No node_id found in event")
    return None


def _extract_payload_data(
    event: dict, event_type: str, payload_field: str
) -> Optional[dict]:
    """Extract payload data from event attributes."""
    logger.info(
        "Extracting payload data", event_type=event_type, payload_field=payload_field
    )
    attrs_key = _get_attributes_key_for_event_type(event_type)

    if not attrs_key or attrs_key not in event:
        logger.info("No attributes key found or key not in event", attrs_key=attrs_key)
        return None

    payloads = (
        event[attrs_key].get(payload_field, {}).get(PayloadField.PAYLOADS.value, [])
    )
    if payloads and PayloadField.DATA.value in payloads[0]:
        result = payloads[0][PayloadField.DATA.value]
        logger.info(
            "Successfully extracted payload data", payload_size=len(str(result))
        )
        return result
    else:
        logger.info("No payload data found in event")
        return None


def _should_include_node_id(node_id: str, target_node_ids: Optional[List[str]]) -> bool:
    """Check if node_id should be included based on target_node_ids filter."""
    result = not target_node_ids or node_id in target_node_ids
    logger.info(
        "Checking if node_id should be included",
        node_id=node_id,
        target_node_ids=target_node_ids,
        included=result,
    )
    return result


def _process_event_with_input_payload(
    event: dict, event_type: EventType
) -> Optional[tuple[str, str]]:
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
        logger.warning(
            "Failed to extract node_id from event", event_type=event_type.value
        )
    return None


def _process_workflow_execution_completed(
    event: dict,
    workflow_node_id: Optional[str],
) -> Optional[tuple[str, str]]:
    """Process WORKFLOW_EXECUTION_COMPLETED event and return (node_id, payload_field) or None."""
    logger.info(
        "Processing WORKFLOW_EXECUTION_COMPLETED event",
        workflow_node_id=workflow_node_id,
    )

    if not workflow_node_id:
        logger.info("Skipping workflow execution completed - no workflow_node_id")
        return None

    logger.info(
        "Found workflow node_id for execution completed", node_id=workflow_node_id
    )
    return workflow_node_id, PayloadField.RESULT.value


def _process_event_with_result_payload(
    event: dict,
    event_type: EventType,
    event_id_field: EventField,
    tracking_events: Dict[int, str],
) -> Optional[tuple[str, str]]:
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
    tracking_events: Dict[int, str],
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


def _add_event_and_payload(
    node_id: str,
    event: dict,
    payload_field: str,
    node_payloads: Dict[str, "NodePayloadData"],
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

    payload = _extract_payload_data(
        event, event.get(EventField.EVENT_TYPE.value), payload_field
    )
    if not payload:
        logger.info(
            "No payload data found, skipping payload assignment", node_id=node_id
        )
        return

    if payload_field == PayloadField.INPUT.value:
        node_payloads[node_id].input_payload = payload
        logger.info("Set input payload for node", node_id=node_id)
    else:
        node_payloads[node_id].output_payload = payload
        logger.info("Set output payload for node", node_id=node_id)


def get_input_from_node_id(events: List[dict], node_id: str) -> Optional[dict]:
    """Get input payload for a specific node ID from events."""
    logger.info(
        "Getting input payload for node", node_id=node_id, event_count=len(events)
    )
    node_data = extract_node_payloads(events, [node_id])
    result = node_data[node_id].input_payload if node_id in node_data else None
    logger.info(
        "Retrieved input payload", node_id=node_id, has_input=result is not None
    )
    return result


def get_output_from_node_id(events: List[dict], node_id: str) -> Optional[dict]:
    """Get output payload for a specific node ID from events."""
    logger.info(
        "Getting output payload for node", node_id=node_id, event_count=len(events)
    )
    node_data = extract_node_payloads(events, [node_id])
    result = node_data[node_id].output_payload if node_id in node_data else None
    logger.info(
        "Retrieved output payload", node_id=node_id, has_output=result is not None
    )
    return result


def get_node_data_from_node_id(
    events: List[dict], node_id: str
) -> Dict[str, "NodePayloadData"]:
    """Get all node data (including input/output payloads and all events) for a specific node ID from events."""
    logger.info(
        "Getting all node data for node", node_id=node_id, event_count=len(events)
    )
    result = extract_node_payloads(events, [node_id])
    logger.info("Retrieved node data", node_id=node_id, found=node_id in result)
    return result


def extract_node_payloads(
    events: List[dict], node_ids: Optional[List[str]] = None
) -> Dict[str, "NodePayloadData"]:
    """Extract all node data including input/output payloads and all events for each node_id from workflow events."""
    logger.info(
        "Starting extraction of all node payloads",
        event_count=len(events),
        target_node_ids=node_ids,
    )
    node_payloads: Dict[str, "NodePayloadData"] = {}
    activity_scheduled_events: Dict[int, str] = {}
    child_workflow_initiated_events: Dict[int, str] = {}
    workflow_node_id: Optional[str] = None

    for event_index, event in enumerate(events):
        event_type = event.get(EventField.EVENT_TYPE.value)
        event_id = event.get(EventField.EVENT_ID.value)
        node_id = None
        payload_field = None
        logger.info(
            "Processing event",
            event_index=event_index,
            event_type=event_type,
            event_id=event_id,
        )

        # Handle workflow execution started
        if event_type == EventType.WORKFLOW_EXECUTION_STARTED.value:
            result = _process_event_with_input_payload(
                event, EventType.WORKFLOW_EXECUTION_STARTED
            )
            if not result:
                continue
            node_id, payload_field = result
            workflow_node_id = node_id

        # Handle workflow execution completed
        if event_type == EventType.WORKFLOW_EXECUTION_COMPLETED.value:
            result = _process_workflow_execution_completed(event, workflow_node_id)
            if not result:
                continue
            node_id, payload_field = result

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

        # Handle activity task scheduled
        if event_type == EventType.ACTIVITY_TASK_SCHEDULED.value:
            result = _process_event_with_input_payload(
                event, EventType.ACTIVITY_TASK_SCHEDULED
            )
            if not result:
                continue
            node_id, payload_field = result
            _track_event_with_node_id(event, node_id, activity_scheduled_events)

        # Handle child workflow execution initiated
        if event_type == EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED.value:
            result = _process_event_with_input_payload(
                event, EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED
            )
            if not result:
                continue
            node_id, payload_field = result
            _track_event_with_node_id(
                event,
                node_id,
                child_workflow_initiated_events,
            )

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

        # Skip if node_id is not in target list
        if not _should_include_node_id(node_id, node_ids):
            continue

        # Add event and node data
        _add_event_and_payload(node_id, event, payload_field, node_payloads)

    logger.info(
        "Completed extraction of all node payloads",
        total_nodes=len(node_payloads),
        node_ids=list(node_payloads.keys()),
        activity_scheduled_count=len(activity_scheduled_events),
        child_workflow_initiated_count=len(child_workflow_initiated_events),
    )
    return node_payloads
