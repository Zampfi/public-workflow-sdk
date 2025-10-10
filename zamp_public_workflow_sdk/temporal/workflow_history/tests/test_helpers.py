from unittest.mock import patch

from zamp_public_workflow_sdk.temporal.workflow_history.helpers import (
    _get_node_id_from_header,
    extract_node_id_from_event,
    _extract_payload_data,
    extract_node_payloads,
)


class TestHelpers:
    """Test cases for temporal helpers functions."""

    def test_get_node_id_from_header_with_data_field(self):
        """Test extracting node_id from header with data field."""
        header_fields = {
            "node_id": {
                "data": "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"  # base64 encoded {"node_id": "workflow-node-1"}
            }
        }

        result = _get_node_id_from_header(header_fields)

        assert result == "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"

    def test_get_node_id_from_header_with_string_data(self):
        """Test extracting node_id from header with string data."""
        header_fields = {"node_id": "workflow-node-1"}

        result = _get_node_id_from_header(header_fields)

        assert result is None

    def test_get_node_id_from_header_with_non_string_data(self):
        """Test extracting node_id from header with non-string data."""
        header_fields = {"node_id": 123}

        result = _get_node_id_from_header(header_fields)

        assert result is None

    def test_get_node_id_from_header_missing_node_id(self):
        """Test extracting node_id from header without node_id field."""
        header_fields = {"other_field": "value"}

        result = _get_node_id_from_header(header_fields)

        assert result is None

    def test_get_node_id_from_header_missing_data_field(self):
        """Test extracting node_id from header without data field."""
        header_fields = {"node_id": {"metadata": {"encoding": "json/plain"}}}

        result = _get_node_id_from_header(header_fields)

        assert result is None

    def test_extract_node_id_from_event_with_header(self):
        """Test extracting node_id from event with header fields."""
        event = {
            "header": {
                "fields": {
                    "node_id": {"data": "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"}
                }
            }
        }

        result = extract_node_id_from_event(event)

        assert result == "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"

    def test_extract_node_id_from_event_without_header(self):
        """Test extracting node_id from event without header."""
        event = {"eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED"}

        result = extract_node_id_from_event(event)

        assert result is None

    def test_extract_node_id_from_event_with_attrs_key(self):
        """Test extracting node_id from event with attributes key."""
        event = {
            "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
            "workflowExecutionStartedEventAttributes": {
                "header": {
                    "fields": {
                        "node_id": {"data": "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"}
                    }
                }
            },
        }

        result = extract_node_id_from_event(event)

        assert result == "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"

    def test_extract_node_id_from_event_without_attrs_key(self):
        """Test extracting node_id from event without attributes key."""
        event = {"eventType": "EVENT_TYPE_UNKNOWN"}

        result = extract_node_id_from_event(event)

        assert result is None

    def test_extract_payload_data_with_valid_payloads(self):
        """Test extracting payload data with valid payloads."""
        event = {
            "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
            "workflowExecutionStartedEventAttributes": {
                "input": {"payloads": [{"data": "eyJ0ZXN0IjogImlucHV0In0="}]}
            },
        }

        result = _extract_payload_data(
            event, "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED", "input"
        )

        assert result == "eyJ0ZXN0IjogImlucHV0In0="

    def test_extract_payload_data_without_attrs_key(self):
        """Test extracting payload data without attributes key."""
        event = {"eventType": "EVENT_TYPE_UNKNOWN"}

        result = _extract_payload_data(event, "EVENT_TYPE_UNKNOWN", "input")

        assert result is None

    def test_extract_payload_data_without_payloads(self):
        """Test extracting payload data without payloads."""
        event = {
            "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
            "workflowExecutionStartedEventAttributes": {"input": {}},
        }

        result = _extract_payload_data(
            event, "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED", "input"
        )

        assert result is None

    def test_extract_payload_data_with_empty_payloads(self):
        """Test extracting payload data with empty payloads."""
        event = {
            "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
            "workflowExecutionStartedEventAttributes": {"input": {"payloads": []}},
        }

        result = _extract_payload_data(
            event, "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED", "input"
        )

        assert result is None

    def test_extract_payload_data_without_data_field(self):
        """Test extracting payload data without data field."""
        event = {
            "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
            "workflowExecutionStartedEventAttributes": {
                "input": {"payloads": [{"metadata": {"encoding": "json/plain"}}]}
            },
        }

        result = _extract_payload_data(
            event, "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED", "input"
        )

        assert result is None

    def test_extract_node_payloads_activity_scheduled(self):
        """Test extracting node payloads for activity scheduled event."""
        events = [
            {
                "eventType": "EVENT_TYPE_ACTIVITY_TASK_SCHEDULED",
                "eventId": 1,
                "activityTaskScheduledEventAttributes": {
                    "header": {
                        "fields": {
                            "node_id": {
                                "data": "eyJub2RlX2lkIjogImFjdGl2aXR5LW5vZGUtMSJ9"
                            }
                        }
                    },
                    "input": {"payloads": [{"data": "eyJhY3Rpdml0eSI6ICJ0ZXN0In0="}]},
                },
            }
        ]

        with patch(
            "zamp_public_workflow_sdk.temporal.workflow_history.helpers.extract_node_id_from_event"
        ) as mock_extract:
            mock_extract.return_value = "activity-node-1"

            result = extract_node_payloads(events)

            assert "activity-node-1" in result
            assert (
                result["activity-node-1"].input_payload
                == "eyJhY3Rpdml0eSI6ICJ0ZXN0In0="
            )

    def test_extract_node_payloads_activity_completed(self):
        """Test extracting node payloads for activity completed event."""
        events = [
            {
                "eventType": "EVENT_TYPE_ACTIVITY_TASK_SCHEDULED",
                "eventId": 1,
                "activityTaskScheduledEventAttributes": {
                    "header": {
                        "fields": {
                            "node_id": {
                                "data": "eyJub2RlX2lkIjogImFjdGl2aXR5LW5vZGUtMSJ9"
                            }
                        }
                    }
                },
            },
            {
                "eventType": "EVENT_TYPE_ACTIVITY_TASK_COMPLETED",
                "activityTaskCompletedEventAttributes": {
                    "result": {"payloads": [{"data": "eyJyZXN1bHQiOiAic3VjY2VzcyJ9"}]},
                    "scheduledEventId": 1,
                },
            },
        ]

        with patch(
            "zamp_public_workflow_sdk.temporal.workflow_history.helpers.extract_node_id_from_event"
        ) as mock_extract:
            mock_extract.side_effect = ["activity-node-1", None]

            result = extract_node_payloads(events)

            assert "activity-node-1" in result
            assert (
                result["activity-node-1"].output_payload
                == "eyJyZXN1bHQiOiAic3VjY2VzcyJ9"
            )

    def test_extract_node_payloads_workflow_completed(self):
        """Test extracting node payloads for workflow completed event."""
        events = [
            {
                "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED",
                "workflowExecutionCompletedEventAttributes": {
                    "result": {"payloads": [{"data": "eyJyZXN1bHQiOiAic3VjY2VzcyJ9"}]}
                },
            },
        ]

        # Since workflow_node_id is not set, workflow completed events are skipped
        result = extract_node_payloads(events)

        # No node data should be created without a workflow_node_id
        assert result == {}

    def test_extract_node_payloads_with_target_node_ids_excluded(self):
        """Test extracting node payloads with target node IDs filter excluding node."""
        events = [
            {
                "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
                "workflowExecutionStartedEventAttributes": {
                    "header": {
                        "fields": {
                            "node_id": {
                                "data": "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"
                            }
                        }
                    },
                    "input": {"payloads": [{"data": "eyJ0ZXN0IjogImlucHV0In0="}]},
                },
            }
        ]

        with patch(
            "zamp_public_workflow_sdk.temporal.workflow_history.helpers.extract_node_id_from_event"
        ) as mock_extract:
            mock_extract.return_value = "workflow-node-1"

            result = extract_node_payloads(events, ["other-node"])

            assert result == {}

    def test_extract_node_payloads_activity_completed_missing_scheduled_event(self):
        """Test extracting node payloads for activity completed with missing scheduled event."""
        events = [
            {
                "eventType": "EVENT_TYPE_ACTIVITY_TASK_COMPLETED",
                "activityTaskCompletedEventAttributes": {
                    "result": {"payloads": [{"data": "eyJyZXN1bHQiOiAic3VjY2VzcyJ9"}]},
                    "scheduledEventId": 999,  # Non-existent event ID
                },
            }
        ]

        result = extract_node_payloads(events)

        assert result == {}

    def test_extract_node_payloads_activity_completed_missing_scheduled_event_id(
        self,
    ):
        """Test extracting node payloads for activity completed with missing scheduled event ID."""
        events = [
            {
                "eventType": "EVENT_TYPE_ACTIVITY_TASK_COMPLETED",
                "activityTaskCompletedEventAttributes": {
                    "result": {"payloads": [{"data": "eyJyZXN1bHQiOiAic3VjY2VzcyJ9"}]}
                    # Missing scheduledEventId
                },
            }
        ]

        result = extract_node_payloads(events)

        assert result == {}

    def test_extract_node_payloads_no_payload_data(self):
        """Test extracting node payloads when no payload data is available."""
        events = [
            {
                "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
                "workflowExecutionStartedEventAttributes": {
                    "header": {
                        "fields": {
                            "node_id": {
                                "data": "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"
                            }
                        }
                    }
                    # Missing input payloads
                },
            }
        ]

        with patch(
            "zamp_public_workflow_sdk.temporal.workflow_history.helpers.extract_node_id_from_event"
        ) as mock_extract:
            mock_extract.return_value = "workflow-node-1"

            result = extract_node_payloads(events)

            # NodePayloadData object is created even when there's no payload data
            assert "workflow-node-1" in result
            assert result["workflow-node-1"].input_payload is None
            assert result["workflow-node-1"].output_payload is None
            assert len(result["workflow-node-1"].node_events) == 1

    def test_extract_node_payloads_empty_payloads(self):
        """Test extracting node payloads with empty payloads array."""
        events = [
            {
                "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
                "workflowExecutionStartedEventAttributes": {
                    "header": {
                        "fields": {
                            "node_id": {
                                "data": "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"
                            }
                        }
                    },
                    "input": {"payloads": []},
                },
            }
        ]

        with patch(
            "zamp_public_workflow_sdk.temporal.workflow_history.helpers.extract_node_id_from_event"
        ) as mock_extract:
            mock_extract.return_value = "workflow-node-1"

            result = extract_node_payloads(events)

            # NodePayloadData object is created even when there's no payload data
            assert "workflow-node-1" in result
            assert result["workflow-node-1"].input_payload is None
            assert result["workflow-node-1"].output_payload is None
            assert len(result["workflow-node-1"].node_events) == 1

    def test_extract_node_payloads_payloads_without_data(self):
        """Test extracting node payloads with payloads missing data field."""
        events = [
            {
                "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
                "workflowExecutionStartedEventAttributes": {
                    "header": {
                        "fields": {
                            "node_id": {
                                "data": "eyJub2RlX2lkIjogIndvcmtmbG93LW5vZGUtMSJ9"
                            }
                        }
                    },
                    "input": {
                        "payloads": [
                            {
                                "metadata": {"encoding": "json/plain"}
                                # Missing data field
                            }
                        ]
                    },
                },
            }
        ]

        with patch(
            "zamp_public_workflow_sdk.temporal.workflow_history.helpers.extract_node_id_from_event"
        ) as mock_extract:
            mock_extract.return_value = "workflow-node-1"

            result = extract_node_payloads(events)

            # NodePayloadData object is created even when there's no payload data
            assert "workflow-node-1" in result
            assert result["workflow-node-1"].input_payload is None
            assert result["workflow-node-1"].output_payload is None
            assert len(result["workflow-node-1"].node_events) == 1
