"""
Unit tests for TemporalHistoryStrategyHandler.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from zamp_public_workflow_sdk.simulation.models.simulation_response import (
    SimulationStrategyOutput,
)
from zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy import (
    MAIN_WORKFLOW_IDENTIFIER,
    TemporalHistoryStrategyHandler,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    WorkflowHistory,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models.node_payload_data import (
    NodePayloadData,
)


class TestTemporalHistoryStrategyHandler:
    """Test cases for TemporalHistoryStrategyHandler class."""

    def test_init(self):
        """Test initialization of TemporalHistoryStrategyHandler."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        assert handler.reference_workflow_id == "workflow-123"
        assert handler.reference_workflow_run_id == "run-456"

    @pytest.mark.asyncio
    async def test_execute_with_provided_history(self):
        """Test execute method with provided temporal history."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Mock workflow history
        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_node_output.return_value = {"result": "success"}

        # Mock _extract_node_output
        with patch.object(handler, "_extract_node_output", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {"activity#1": {"result": "success"}}

            result = await handler.execute(
                node_ids=["activity#1"],
                temporal_history=mock_history,
            )

            assert isinstance(result, SimulationStrategyOutput)
            assert result.node_outputs == {"activity#1": {"result": "success"}}
            mock_extract.assert_called_once_with(["activity#1"])

    @pytest.mark.asyncio
    async def test_execute_without_provided_history(self):
        """Test execute method without provided temporal history (fetches it)."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Mock workflow history
        mock_history = Mock(spec=WorkflowHistory)

        # Mock _fetch_temporal_history and _extract_node_output
        with patch.object(handler, "_fetch_temporal_history", new_callable=AsyncMock) as mock_fetch:
            with patch.object(handler, "_extract_node_output", new_callable=AsyncMock) as mock_extract:
                mock_fetch.return_value = mock_history
                mock_extract.return_value = {"activity#1": {"result": "success"}}

                result = await handler.execute(node_ids=["activity#1"])

                assert isinstance(result, SimulationStrategyOutput)
                assert result.node_outputs == {"activity#1": {"result": "success"}}
                mock_fetch.assert_called_once_with(["activity#1"])
                mock_extract.assert_called_once_with(["activity#1"])

    @pytest.mark.asyncio
    async def test_execute_fetch_returns_none(self):
        """Test execute method when fetch returns None."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Mock _fetch_temporal_history to return None
        with patch.object(handler, "_fetch_temporal_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None

            with pytest.raises(Exception, match="Failed to fetch temporal history"):
                await handler.execute(node_ids=["activity#1"])

            mock_fetch.assert_called_once_with(["activity#1"])

    @pytest.mark.asyncio
    async def test_execute_with_exception(self):
        """Test execute method when an exception occurs."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_history = Mock(spec=WorkflowHistory)

        # Mock _extract_node_output to raise exception
        with patch.object(handler, "_extract_node_output", new_callable=AsyncMock) as mock_extract:
            mock_extract.side_effect = Exception("Test error")

            with pytest.raises(Exception, match="Test error"):
                await handler.execute(
                    node_ids=["activity#1"],
                    temporal_history=mock_history,
                )

    @pytest.mark.asyncio
    async def test_fetch_temporal_history_success(self):
        """Test _fetch_temporal_history with successful fetch."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_workflow_history = Mock(spec=WorkflowHistory)

        # Patch at the import location in the function
        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_child_workflow", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_workflow_history

            result = await handler._fetch_temporal_history(node_ids=["activity#1"])

            assert result == mock_workflow_history
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][0] == "FetchTemporalWorkflowHistoryWorkflow"
            assert call_args[1]["result_type"] is not None

    @pytest.mark.asyncio
    async def test_fetch_temporal_history_with_custom_ids(self):
        """Test _fetch_temporal_history with custom workflow_id and run_id."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_workflow_history = Mock(spec=WorkflowHistory)

        # Patch at the import location in the function
        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_child_workflow", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_workflow_history

            result = await handler._fetch_temporal_history(
                node_ids=["activity#1"],
                workflow_id="custom-workflow-id",
                run_id="custom-run-id",
            )

            assert result == mock_workflow_history
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            input_arg = call_args[0][1]
            assert input_arg.workflow_id == "custom-workflow-id"
            assert input_arg.run_id == "custom-run-id"

    @pytest.mark.asyncio
    async def test_fetch_temporal_history_failure(self):
        """Test _fetch_temporal_history with exception."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Patch at the import location in the function
        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_child_workflow", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = Exception("Fetch failed")

            result = await handler._fetch_temporal_history(node_ids=["activity#1"])

            assert result is None

    @pytest.mark.asyncio
    async def test_extract_node_output_main_workflow_only(self):
        """Test _extract_node_output with only main workflow nodes."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_node_output.side_effect = lambda node_id: {"output": f"output-{node_id}"}

        # Set the cached history
        handler.workflow_histories_map["main_workflow"] = mock_history

        result = await handler._extract_node_output(
            node_ids=["activity#1", "activity#2"],
        )

        assert result == {
            "activity#1": {"output": "output-activity#1"},
            "activity#2": {"output": "output-activity#2"},
        }
        assert mock_history.get_node_output.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_node_output_with_child_workflow(self):
        """Test _extract_node_output with child workflow nodes."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_node_output.return_value = {"output": "main-output"}

        # Set the cached history
        handler.workflow_histories_map["main_workflow"] = mock_history

        # Mock _extract_child_workflow_node_outputs
        with patch.object(handler, "_extract_child_workflow_node_outputs", new_callable=AsyncMock) as mock_child:
            mock_child.return_value = {"Child#1.activity#1": {"output": "child-output"}}

            result = await handler._extract_node_output(
                node_ids=["activity#1", "Child#1.activity#1"],
            )

            assert "activity#1" in result
            assert "Child#1.activity#1" in result
            assert result["Child#1.activity#1"] == {"output": "child-output"}

    @pytest.mark.asyncio
    async def test_extract_node_output_with_exception(self):
        """Test _extract_node_output when an exception occurs."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_node_output.side_effect = Exception("Extract error")

        # Set the cached history
        handler.workflow_histories_map["main_workflow"] = mock_history

        with pytest.raises(Exception, match="Extract error"):
            await handler._extract_node_output(
                node_ids=["activity#1"],
            )

    def test_extract_main_workflow_node_outputs(self):
        """Test _extract_main_workflow_node_outputs method."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_node_output.side_effect = lambda node_id: {"output": f"output-{node_id}"}

        result = handler._extract_main_workflow_node_outputs(
            temporal_history=mock_history,
            node_ids=["activity#1", "activity#2"],
        )

        assert result == {
            "activity#1": {"output": "output-activity#1"},
            "activity#2": {"output": "output-activity#2"},
        }

    @pytest.mark.asyncio
    async def test_extract_child_workflow_node_outputs_success(self):
        """Test _extract_child_workflow_node_outputs with successful extraction."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_child_history = Mock(spec=WorkflowHistory)

        # Mock child history node data
        mock_node_data = {
            "Child#1.activity#1": NodePayloadData(
                node_id="Child#1.activity#1",
                input_payload=None,
                output_payload={"result": "child-result"},
                node_events=[],
            )
        }
        mock_child_history.get_nodes_data.return_value = mock_node_data

        # Mock _fetch_nested_child_workflow_history
        with patch.object(handler, "_fetch_nested_child_workflow_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_child_history

            result = await handler._extract_child_workflow_node_outputs(
                parent_history=mock_parent_history,
                child_workflow_id="Child#1",
                node_ids=["Child#1.activity#1"],
            )

            assert result == {"Child#1.activity#1": {"result": "child-result"}}

    @pytest.mark.asyncio
    async def test_extract_child_workflow_node_outputs_not_found(self):
        """Test _extract_child_workflow_node_outputs when child history is not found."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_parent_history = Mock(spec=WorkflowHistory)

        # Mock _fetch_nested_child_workflow_history to return None
        with patch.object(handler, "_fetch_nested_child_workflow_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None

            with pytest.raises(Exception, match="Failed to fetch child workflow history"):
                await handler._extract_child_workflow_node_outputs(
                    parent_history=mock_parent_history,
                    child_workflow_id="Child#1",
                    node_ids=["Child#1.activity#1", "Child#1.activity#2"],
                )

    @pytest.mark.asyncio
    async def test_extract_child_workflow_node_outputs_missing_node(self):
        """Test _extract_child_workflow_node_outputs when node is missing in child history."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_child_history = Mock(spec=WorkflowHistory)

        # Mock child history with empty node data
        mock_child_history.get_nodes_data.return_value = {}

        # Mock _fetch_nested_child_workflow_history
        with patch.object(handler, "_fetch_nested_child_workflow_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_child_history

            result = await handler._extract_child_workflow_node_outputs(
                parent_history=mock_parent_history,
                child_workflow_id="Child#1",
                node_ids=["Child#1.activity#1"],
            )

            assert result == {"Child#1.activity#1": None}

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_single_level(self):
        """Test _fetch_nested_child_workflow_history with single level nesting."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_parent_history.get_child_workflow_workflow_id_run_id.return_value = (
            "child-workflow-id",
            "child-run-id",
        )

        mock_child_history = Mock(spec=WorkflowHistory)

        # Mock _fetch_temporal_history
        with patch.object(handler, "_fetch_temporal_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_child_history

            result = await handler._fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed={},
            )

            assert result == mock_child_history
            mock_parent_history.get_child_workflow_workflow_id_run_id.assert_called_once_with("Child#1")

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_with_cache(self):
        """Test _fetch_nested_child_workflow_history using cached history."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_cached_history = Mock(spec=WorkflowHistory)

        # Use cached history
        handler.workflow_histories_map["Child#1"] = mock_cached_history

        result = await handler._fetch_nested_child_workflow_history(
            parent_workflow_history=mock_parent_history,
            full_child_path="Child#1",
            node_ids=["Child#1.activity#1"],
            workflow_nodes_needed={},
        )

        assert result == mock_cached_history

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_no_workflow_id(self):
        """Test _fetch_nested_child_workflow_history when workflow_id not found."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_parent_history.get_child_workflow_workflow_id_run_id.side_effect = ValueError(
            "No node data found for child workflow with node_id=Child#1"
        )

        with pytest.raises(Exception, match="Failed to get workflow_id and run_id"):
            await handler._fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed={},
            )

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_nested_levels(self):
        """Test _fetch_nested_child_workflow_history with multiple nested levels."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_parent_history.get_child_workflow_workflow_id_run_id.return_value = (
            "parent-workflow-id",
            "parent-run-id",
        )

        mock_intermediate_history = Mock(spec=WorkflowHistory)
        mock_intermediate_history.get_child_workflow_workflow_id_run_id.return_value = (
            "child-workflow-id",
            "child-run-id",
        )

        mock_final_history = Mock(spec=WorkflowHistory)

        # Mock _fetch_temporal_history
        with patch.object(handler, "_fetch_temporal_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [mock_intermediate_history, mock_final_history]

            result = await handler._fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Parent#1.Child#1",
                node_ids=["Parent#1.Child#1.activity#1"],
                workflow_nodes_needed={},
            )

            assert result == mock_final_history
            assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_fetch_fails(self):
        """Test _fetch_nested_child_workflow_history when fetch fails."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_parent_history.get_child_workflow_workflow_id_run_id.return_value = (
            "child-workflow-id",
            "child-run-id",
        )

        # Mock _fetch_temporal_history to return None
        with patch.object(handler, "_fetch_temporal_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None

            result = await handler._fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed={},
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_with_workflow_nodes_needed(self):
        """Test _fetch_nested_child_workflow_history with pre-collected workflow nodes."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_parent_history.get_child_workflow_workflow_id_run_id.return_value = (
            "child-workflow-id",
            "child-run-id",
        )

        mock_child_history = Mock(spec=WorkflowHistory)

        workflow_nodes_needed = {"Child#1": ["Child#1.activity#1", "Child#1.activity#2"]}

        # Mock _fetch_temporal_history
        with patch.object(handler, "_fetch_temporal_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_child_history

            result = await handler._fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed=workflow_nodes_needed,
            )

            assert result == mock_child_history
            # Check that it used workflow_nodes_needed
            call_args = mock_fetch.call_args
            assert call_args[1]["node_ids"] == ["Child#1.activity#1", "Child#1.activity#2"]

    def test_get_workflow_path_from_node(self):
        """Test _get_workflow_path_from_node method."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Test normal case
        result = handler._get_workflow_path_from_node(
            node_id="Parent#1.Child#1.activity#1",
            child_workflow_id="Child#1",
        )
        assert result == "Parent#1.Child#1"

        # Test when child_workflow_id is at the start
        result = handler._get_workflow_path_from_node(
            node_id="Child#1.activity#1",
            child_workflow_id="Child#1",
        )
        assert result == "Child#1"

        # Test when child_workflow_id is not found
        result = handler._get_workflow_path_from_node(
            node_id="Parent#1.activity#1",
            child_workflow_id="Child#1",
        )
        assert result == "Child#1"

    def test_collect_nodes_per_workflow(self):
        """Test _collect_nodes_per_workflow method."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Test with simple nodes
        result = handler._collect_nodes_per_workflow(["Parent#1.query#1", "Parent#1.Child#1.activity#1"])

        assert "Parent#1" in result
        assert "Parent#1.query#1" in result["Parent#1"]
        assert "Parent#1.Child#1" in result["Parent#1"]
        assert "Parent#1.Child#1" in result
        assert "Parent#1.Child#1.activity#1" in result["Parent#1.Child#1"]

        # Test with single-level nodes
        result = handler._collect_nodes_per_workflow(["activity#1", "activity#2"])
        # Single-level nodes don't create any workflow entries
        assert result == {}

        # Test with multiple nested levels
        result = handler._collect_nodes_per_workflow(["Parent#1.Child#1.GrandChild#1.activity#1"])
        assert "Parent#1" in result
        assert "Parent#1.Child#1" in result
        assert "Parent#1.Child#1.GrandChild#1" in result

    def test_group_nodes_by_parent_workflow(self):
        """Test _group_nodes_by_parent_workflow method."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Test with single-level nodes
        result = handler._group_nodes_by_parent_workflow(["activity#1", "activity#2"])
        assert result == {MAIN_WORKFLOW_IDENTIFIER: ["activity#1", "activity#2"]}

        # Test with child workflow nodes
        result = handler._group_nodes_by_parent_workflow(["activity#1", "Child#1.activity#1", "Child#1.activity#2"])
        assert MAIN_WORKFLOW_IDENTIFIER in result
        assert "Child#1" in result
        assert result[MAIN_WORKFLOW_IDENTIFIER] == ["activity#1"]
        assert result["Child#1"] == ["Child#1.activity#1", "Child#1.activity#2"]

        # Test with nested child workflows
        result = handler._group_nodes_by_parent_workflow(["Parent#1.Child#1.activity#1", "Parent#1.activity#1"])
        assert "Child#1" in result
        assert "Parent#1" in result
        assert result["Child#1"] == ["Parent#1.Child#1.activity#1"]
        assert result["Parent#1"] == ["Parent#1.activity#1"]

        # Test with deeply nested workflows
        result = handler._group_nodes_by_parent_workflow(["Parent#1.Child#1.GrandChild#1.activity#1"])
        assert result == {"GrandChild#1": ["Parent#1.Child#1.GrandChild#1.activity#1"]}
