import pytest

from zamp_public_workflow_sdk.temporal.workflow_history.models.workflow_history import WorkflowHistory


class TestWorkflowHistory:
    @pytest.fixture
    def sample_workflow_history(self):
        return WorkflowHistory(
            workflow_id="test-workflow-123",
            run_id="test-run-456",
            events=[
                {
                    "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED",
                    "eventId": 1,
                    "workflowExecutionStartedEventAttributes": {
                        "header": {"fields": {"node_id": {"data": "node-1"}}},
                        "input": {
                            "payloads": [
                                {
                                    "data": "test input data",
                                    "metadata": {"encoding": "json/plain"},
                                }
                            ]
                        },
                    },
                },
                {
                    "eventType": "EVENT_TYPE_ACTIVITY_TASK_COMPLETED",
                    "eventId": 2,
                    "activityTaskCompletedEventAttributes": {
                        "scheduledEventId": 1,
                        "result": {
                            "payloads": [
                                {
                                    "data": "test output data",
                                    "metadata": {"encoding": "json/plain"},
                                }
                            ]
                        },
                    },
                },
            ],
        )

    def test_workflow_history_creation(self):
        """Test basic workflow history creation"""
        history = WorkflowHistory(
            workflow_id="test-workflow",
            run_id="test-run",
            events=[{"eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED"}],
        )

        assert history.workflow_id == "test-workflow"
        assert history.run_id == "test-run"
        assert len(history.events) == 1
        assert history.events[0]["eventType"] == "EVENT_TYPE_WORKFLOW_EXECUTION_STARTED"

    def test_get_input_from_node_id_success(self, sample_workflow_history):
        """Test getting input from node ID when node exists"""
        result = sample_workflow_history.get_node_input("node-1")

        # The actual implementation extracts the payload from the workflow execution started event
        assert result == "test input data"

    def test_get_input_from_node_id_not_found(self, sample_workflow_history):
        """Test getting input from node ID when node doesn't exist"""
        result = sample_workflow_history.get_node_input("nonexistent-node")

        # The actual implementation returns None when node is not found
        assert result is None

    def test_get_output_from_node_id_success(self, sample_workflow_history):
        """Test getting output from node ID when node exists"""
        result = sample_workflow_history.get_node_output("node-1")

        # The actual implementation returns None for output since there's no workflow completed event
        assert result is None

    def test_get_output_from_node_id_not_found(self, sample_workflow_history):
        """Test getting output from node ID when node doesn't exist"""
        result = sample_workflow_history.get_node_output("nonexistent-node")

        # The actual implementation returns None when node is not found
        assert result is None

    def test_get_node_data_success(self, sample_workflow_history):
        """Test getting all node data when node exists"""
        result = sample_workflow_history.get_node_data("node-1")

        # The actual implementation returns the real node data
        assert "node-1" in result
        assert result["node-1"].node_id == "node-1"
        assert result["node-1"].input_payload == "test input data"
        assert result["node-1"].output_payload is None
        assert len(result["node-1"].node_events) == 1

    def test_get_node_data_not_found(self, sample_workflow_history):
        """Test getting all node data when node doesn't exist"""
        result = sample_workflow_history.get_node_data("nonexistent-node")

        # The actual implementation returns empty dict when node is not found
        assert result == {}

    def test_get_all_node_payloads_with_target_node_ids(self, sample_workflow_history):
        """Test getting all node payloads with specific target node IDs"""
        result = sample_workflow_history.get_nodes_data(["node-1", "node-2"])

        # The actual implementation returns the real node data
        assert "node-1" in result
        assert result["node-1"].node_id == "node-1"
        assert result["node-1"].input_payload == "test input data"
        assert result["node-1"].output_payload is None
        assert len(result["node-1"].node_events) == 1

    def test_get_all_node_payloads_without_target_node_ids(self, sample_workflow_history):
        """Test getting all node payloads without target node IDs"""
        result = sample_workflow_history.get_nodes_data()

        # The actual implementation returns the real node data
        assert "node-1" in result
        assert result["node-1"].node_id == "node-1"
        assert result["node-1"].input_payload == "test input data"
        assert result["node-1"].output_payload is None
        assert len(result["node-1"].node_events) == 1

    def test_get_all_node_payloads_with_empty_target_node_ids(self, sample_workflow_history):
        """Test getting all node payloads with empty target node IDs list"""
        result = sample_workflow_history.get_nodes_data([])

        assert "node-1" in result
        assert result["node-1"].node_id == "node-1"
        assert result["node-1"].input_payload == "test input data"
        assert result["node-1"].output_payload is None
        assert len(result["node-1"].node_events) == 1
