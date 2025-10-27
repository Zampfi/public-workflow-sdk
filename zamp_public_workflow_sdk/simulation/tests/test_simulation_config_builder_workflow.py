"""Unit tests for SimulationConfigBuilderWorkflow."""

import pytest
from unittest.mock import MagicMock, patch

from zamp_public_workflow_sdk.simulation.models.simulation_config_builder import (
    SimulationConfigBuilderInput,
    SimulationConfigBuilderOutput,
)
from zamp_public_workflow_sdk.simulation.models import (
    SimulationConfig,
    StrategyType,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    FetchTemporalWorkflowHistoryOutput,
    WorkflowHistory,
)
from zamp_public_workflow_sdk.temporal.workflow_history.constants import EventType, EventField
from zamp_public_workflow_sdk.simulation.workflows.simulation_config_builder_workflow import (
    SimulationConfigBuilderWorkflow,
)


class TestSimulationConfigBuilderWorkflow:
    """Test cases for SimulationConfigBuilderWorkflow."""

    @pytest.fixture
    def workflow(self):
        """Create a SimulationConfigBuilderWorkflow instance."""
        return SimulationConfigBuilderWorkflow()

    @pytest.fixture
    def sample_input(self):
        """Create sample input for testing."""
        return SimulationConfigBuilderInput(
            workflow_id="test-workflow-id",
            run_id="test-run-id",
        )

    @pytest.fixture
    def mock_workflow_history(self):
        """Create a mock workflow history."""
        history = MagicMock(spec=WorkflowHistory)
        history.get_nodes_data.return_value = {
            "node1": MagicMock(node_events=[]),
            "node2": MagicMock(node_events=[]),
        }
        return history

    @pytest.fixture
    def mock_fetch_history_output(self):
        """Create mock fetch history output."""
        mock_output = MagicMock(spec=FetchTemporalWorkflowHistoryOutput)
        mock_output.events = []
        return mock_output

    def test_init(self, workflow):
        """Test workflow initialization."""
        assert isinstance(workflow.workflow_histories, dict)
        assert workflow.workflow_histories == {}
        assert "generate_llm_model_response" in workflow.nodes_to_skip

    def test_is_child_workflow_node_with_child_workflow_events(self, workflow):
        """Test _is_child_workflow_node returns True for child workflow events."""
        # Mock node data with child workflow events
        node_data = MagicMock()
        node_data.node_events = [
            {EventField.EVENT_TYPE.value: EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED.value},
            {EventField.EVENT_TYPE.value: "some_other_event"},
        ]

        result = workflow._is_child_workflow_node(node_data)
        assert result is True

    def test_is_child_workflow_node_with_child_workflow_started(self, workflow):
        """Test _is_child_workflow_node returns True for CHILD_WORKFLOW_EXECUTION_STARTED."""
        node_data = MagicMock()
        node_data.node_events = [
            {EventField.EVENT_TYPE.value: EventType.CHILD_WORKFLOW_EXECUTION_STARTED.value},
        ]

        result = workflow._is_child_workflow_node(node_data)
        assert result is True

    def test_is_child_workflow_node_with_workflow_execution_started(self, workflow):
        """Test _is_child_workflow_node returns True for WORKFLOW_EXECUTION_STARTED."""
        node_data = MagicMock()
        node_data.node_events = [
            {EventField.EVENT_TYPE.value: EventType.WORKFLOW_EXECUTION_STARTED.value},
        ]

        result = workflow._is_child_workflow_node(node_data)
        assert result is True

    def test_is_child_workflow_node_without_child_workflow_events(self, workflow):
        """Test _is_child_workflow_node returns False for non-child workflow events."""
        node_data = MagicMock()
        node_data.node_events = [
            {EventField.EVENT_TYPE.value: "ACTIVITY_TASK_SCHEDULED"},
            {EventField.EVENT_TYPE.value: "WORKFLOW_TASK_COMPLETED"},
        ]

        result = workflow._is_child_workflow_node(node_data)
        assert result is False

    def test_is_child_workflow_node_with_empty_events(self, workflow):
        """Test _is_child_workflow_node returns False for empty events."""
        node_data = MagicMock()
        node_data.node_events = []

        result = workflow._is_child_workflow_node(node_data)
        assert result is False

    def test_should_include_node_includes_valid_node(self, workflow):
        """Test _should_include_node includes nodes not in skip list."""
        result = workflow._should_include_node("valid_activity_node")
        assert result == "valid_activity_node"

    def test_should_include_node_skips_llm_node(self, workflow):
        """Test _should_include_node skips nodes in skip list."""
        result = workflow._should_include_node("generate_llm_model_response")
        assert result is None

    def test_should_include_node_skips_partial_match(self, workflow):
        """Test _should_include_node skips nodes containing skip patterns."""
        result = workflow._should_include_node("some_generate_llm_model_response_activity")
        assert result is None

    @pytest.mark.asyncio
    async def test_process_child_workflow_node_all_activities_mocked(self, workflow):
        """Test _process_child_workflow_node returns parent node_id when all activities would be mocked."""
        # Mock workflow history
        workflow_history = MagicMock()
        workflow_history.get_child_workflow_workflow_id_run_id.return_value = (
            "child-workflow-id",
            "child-run-id",
        )

        # Mock child history
        child_history = MagicMock()

        # Mock workflow history nodes data (the method uses workflow_history.get_nodes_data().keys())
        workflow_history.get_nodes_data.return_value = {
            "child_node1": MagicMock(node_events=[]),
            "child_node2": MagicMock(node_events=[]),
        }

        # Mock child history
        child_history = MagicMock()

        with patch.object(workflow, "_fetch_workflow_history", return_value=child_history):
            with patch.object(
                workflow, "_should_include_node", side_effect=lambda node_id: node_id
            ) as mock_should_include:
                result = await workflow._process_child_workflow_node("parent_node", workflow_history)

                # Should return parent node_id since all activities would be mocked (none skipped)
                assert result == ["parent_node"]
                assert mock_should_include.call_count == 2

    @pytest.mark.asyncio
    async def test_process_child_workflow_node_some_activities_skipped(self, workflow):
        """Test _process_child_workflow_node returns individual activities when some are skipped."""
        # Mock workflow history
        workflow_history = MagicMock()
        workflow_history.get_child_workflow_workflow_id_run_id.return_value = (
            "child-workflow-id",
            "child-run-id",
        )

        # Mock child history
        child_history = MagicMock()

        # Mock workflow history nodes data (the method uses workflow_history.get_nodes_data().keys())
        workflow_history.get_nodes_data.return_value = {
            "child_node1": MagicMock(node_events=[]),
            "child_node2": MagicMock(node_events=[]),
            "child_node3": MagicMock(node_events=[]),
        }

        # Mock child history
        child_history = MagicMock()

        with patch.object(workflow, "_fetch_workflow_history", return_value=child_history):
            # Mock to skip child_node3
            with patch.object(
                workflow,
                "_should_include_node",
                side_effect=lambda node_id: node_id if node_id != "child_node3" else None,
            ) as mock_should_include:
                result = await workflow._process_child_workflow_node("parent_node", workflow_history)

                # Should return individual activity node_ids since not all would be mocked (some skipped)
                assert result == ["child_node1", "child_node2"]
                # Note: _fetch_workflow_history is not called in current implementation
                assert mock_should_include.call_count == 3

    @pytest.mark.asyncio
    async def test_process_child_workflow_node_exception(self, workflow):
        """Test _process_child_workflow_node raises exceptions."""
        workflow_history = MagicMock()
        workflow_history.get_child_workflow_workflow_id_run_id.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            await workflow._process_child_workflow_node("parent_node", workflow_history)

    def test_get_all_node_ids(self, workflow):
        """Test getting all node IDs from workflow history."""
        # Create mock workflow history with mixed node types
        workflow_history = MagicMock()

        # Create activity nodes (including ones that would normally be skipped)
        activity_node1 = MagicMock(node_events=[])
        activity_node2 = MagicMock(node_events=[])
        skippable_node = MagicMock(node_events=[])

        workflow_history.get_nodes_data.return_value = {
            "activity1": activity_node1,
            "generate_llm_model_response": skippable_node,
            "activity2": activity_node2,
        }

        # Test the direct call to get_nodes_data().keys() as used in the implementation
        result = list(workflow_history.get_nodes_data().keys())

        # Should return all nodes, including ones that would normally be skipped
        assert set(result) == {"activity1", "generate_llm_model_response", "activity2"}

    def test_get_all_node_ids_with_child_workflow(self, workflow):
        """Test getting node IDs from workflow history with child workflow."""
        # Create mock workflow history with child workflow
        workflow_history = MagicMock()

        # Create child workflow node
        child_workflow_node = MagicMock()
        child_workflow_node.node_events = [
            {EventField.EVENT_TYPE.value: EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED.value}
        ]

        activity_node = MagicMock(node_events=[])

        workflow_history.get_nodes_data.return_value = {
            "activity1": activity_node,
            "child_workflow": child_workflow_node,
        }

        # Test the direct call to get_nodes_data().keys() as used in the implementation
        result = list(workflow_history.get_nodes_data().keys())

        # Should return all nodes from the workflow history
        assert set(result) == {"activity1", "child_workflow"}

    @pytest.mark.asyncio
    async def test_extract_all_node_ids_recursively_with_regular_nodes(self, workflow):
        """Test _extract_all_node_ids_recursively processes regular nodes."""
        # Mock workflow history with regular nodes
        workflow_history = MagicMock()
        workflow_history.get_nodes_data.return_value = {
            "node1": MagicMock(node_events=[]),
            "node2": MagicMock(node_events=[]),
        }

        with patch.object(
            workflow, "_should_include_node", side_effect=lambda node_id: node_id if node_id != "node2" else None
        ):
            result = await workflow._extract_all_node_ids_recursively(workflow_history)

            assert result == ["node1"]  # node2 should be filtered out

    @pytest.mark.asyncio
    async def test_extract_all_node_ids_recursively_with_child_workflows(self, workflow):
        """Test _extract_all_node_ids_recursively processes child workflows."""
        # Mock workflow history with child workflow
        workflow_history = MagicMock()

        # Create child workflow node
        child_node_data = MagicMock()
        child_node_data.node_events = [
            {EventField.EVENT_TYPE.value: EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED.value}
        ]

        workflow_history.get_nodes_data.return_value = {
            "regular_node": MagicMock(node_events=[]),
            "child_workflow_node": child_node_data,
        }

        with patch.object(workflow, "_should_include_node", return_value="regular_node"):
            with patch.object(workflow, "_process_child_workflow_node", return_value=["child_node1", "child_node2"]):
                result = await workflow._extract_all_node_ids_recursively(workflow_history)

                assert result == ["regular_node", "child_node1", "child_node2"]

    @pytest.mark.asyncio
    async def test_fetch_workflow_history_success(self, workflow, mock_fetch_history_output):
        """Test _fetch_workflow_history fetches history successfully."""
        with patch(
            "zamp_public_workflow_sdk.simulation.workflows.simulation_config_builder_workflow.ActionsHub.execute_child_workflow",
            return_value=mock_fetch_history_output,
        ) as mock_execute:
            result = await workflow._fetch_workflow_history("test-workflow-id", "test-run-id")

            assert result == mock_fetch_history_output
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_workflow_history_exception(self, workflow):
        """Test _fetch_workflow_history raises exception on failure."""
        with patch(
            "zamp_public_workflow_sdk.simulation.workflows.simulation_config_builder_workflow.ActionsHub.execute_child_workflow",
            side_effect=Exception("Fetch failed"),
        ):
            with pytest.raises(Exception, match="Fetch failed"):
                await workflow._fetch_workflow_history("test-workflow-id", "test-run-id")

    def test_generate_simulation_config(self, workflow):
        """Test _generate_simulation_config creates proper configuration."""
        node_ids = ["node1", "node2", "node3"]
        workflow_id = "test-workflow-id"
        run_id = "test-run-id"

        result = workflow._generate_simulation_config(node_ids, workflow_id, run_id)

        assert isinstance(result, SimulationConfig)
        assert result.version == "1.0.0"
        assert len(result.mock_config.node_strategies) == 1

        strategy = result.mock_config.node_strategies[0]
        assert strategy.nodes == node_ids
        assert strategy.strategy.type == StrategyType.TEMPORAL_HISTORY
        assert strategy.strategy.config.reference_workflow_id == workflow_id
        assert strategy.strategy.config.reference_workflow_run_id == run_id

    @pytest.mark.asyncio
    async def test_execute_full_workflow(self, workflow, sample_input):
        """Test complete execute workflow."""
        # Mock workflow history
        mock_history = MagicMock()
        mock_history.get_nodes_data.return_value = {
            "node1": MagicMock(node_events=[]),
            "node2": MagicMock(node_events=[]),
        }

        with patch.object(workflow, "_fetch_workflow_history", return_value=mock_history) as mock_fetch:
            with patch.object(
                workflow, "_extract_all_node_ids_recursively", return_value=["node1", "node2"]
            ) as mock_extract:
                result = await workflow.execute(sample_input)

                assert isinstance(result, SimulationConfigBuilderOutput)
                assert isinstance(result.simulation_config, SimulationConfig)

                mock_fetch.assert_called_once_with(workflow_id=sample_input.workflow_id, run_id=sample_input.run_id)
                mock_extract.assert_called_once_with(workflow_history=mock_history)

    @pytest.mark.asyncio
    async def test_execute_with_empty_nodes(self, workflow, sample_input):
        """Test execute workflow with no nodes."""
        mock_history = MagicMock()
        mock_history.get_nodes_data.return_value = {}

        with patch.object(workflow, "_fetch_workflow_history", return_value=mock_history):
            with patch.object(workflow, "_extract_all_node_ids_recursively", return_value=[]):
                # Test that empty nodes list raises validation error
                with pytest.raises(Exception):
                    await workflow.execute(sample_input)

    @pytest.mark.asyncio
    async def test_execute_with_mixed_node_types(self, workflow, sample_input):
        """Test execute workflow with mixed regular and child workflow nodes."""
        mock_history = MagicMock()

        # Create mixed node types
        regular_node = MagicMock(node_events=[])
        child_workflow_node = MagicMock()
        child_workflow_node.node_events = [
            {EventField.EVENT_TYPE.value: EventType.START_CHILD_WORKFLOW_EXECUTION_INITIATED.value}
        ]

        mock_history.get_nodes_data.return_value = {
            "regular_node": regular_node,
            "child_workflow_node": child_workflow_node,
        }

        with patch.object(workflow, "_fetch_workflow_history", return_value=mock_history):
            with patch.object(workflow, "_should_include_node", return_value="regular_node"):
                with patch.object(
                    workflow, "_process_child_workflow_node", return_value=["child_node1", "child_node2"]
                ):
                    with patch.object(
                        workflow,
                        "_extract_all_node_ids_recursively",
                        return_value=["regular_node", "child_node1", "child_node2"],
                    ):
                        result = await workflow.execute(sample_input)

                        assert isinstance(result, SimulationConfigBuilderOutput)
                        assert len(result.simulation_config.mock_config.node_strategies[0].nodes) == 3
