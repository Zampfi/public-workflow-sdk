"""
Unit tests for TemporalHistoryStrategyHandler.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from zamp_public_workflow_sdk.simulation.helper import (
    MAIN_WORKFLOW_IDENTIFIER,
    collect_nodes_per_workflow,
    extract_child_workflow_node_payloads,
    extract_main_workflow_node_payloads,
    extract_node_payload,
    fetch_nested_child_workflow_history,
    fetch_temporal_history,
    get_workflow_path_from_node,
    group_nodes_by_parent_workflow,
)
from zamp_public_workflow_sdk.simulation.models import NodePayload
from zamp_public_workflow_sdk.simulation.models.simulation_response import (
    SimulationStrategyOutput,
)
from zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy import (
    TemporalHistoryStrategyHandler,
)
from zamp_public_workflow_sdk.temporal.workflow_history.models import (
    WorkflowHistory,
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
        """Test execute method with fetching temporal history."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Mock workflow history
        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_node_output.return_value = {"result": "success"}

        # Mock fetch_temporal_history and extract_node_payload
        with patch(
            "zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy.fetch_temporal_history",
            new_callable=AsyncMock,
        ) as mock_fetch:
            with patch(
                "zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy.extract_node_payload",
                new_callable=AsyncMock,
            ) as mock_extract:
                mock_fetch.return_value = mock_history
                mock_extract.return_value = {
                    "activity#1": NodePayload(
                        node_id="activity#1", input_payload=None, output_payload={"result": "success"}
                    )
                }

                result = await handler.execute(
                    node_ids=["activity#1"],
                )

                assert isinstance(result, SimulationStrategyOutput)
                assert "activity#1" in result.node_id_to_payload_map
                assert isinstance(result.node_id_to_payload_map["activity#1"], NodePayload)
                # The mock returns plain dict which gets converted to NodePayload
                mock_fetch.assert_called_once()
                mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_without_provided_history(self):
        """Test execute method without provided temporal history (fetches it)."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Mock workflow history
        mock_history = Mock(spec=WorkflowHistory)

        # Mock fetch_temporal_history and extract_node_payload
        with patch(
            "zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy.fetch_temporal_history",
            new_callable=AsyncMock,
        ) as mock_fetch:
            with patch(
                "zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy.extract_node_payload",
                new_callable=AsyncMock,
            ) as mock_extract:
                mock_fetch.return_value = mock_history
                mock_extract.return_value = {
                    "activity#1": NodePayload(
                        node_id="activity#1", input_payload=None, output_payload={"result": "success"}
                    )
                }

                result = await handler.execute(node_ids=["activity#1"])

                assert isinstance(result, SimulationStrategyOutput)
                assert "activity#1" in result.node_id_to_payload_map
                assert isinstance(result.node_id_to_payload_map["activity#1"], NodePayload)
                # The mock returns plain dict which gets converted to NodePayload
                mock_fetch.assert_called_once()
                mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_fetch_returns_none(self):
        """Test execute method when fetch returns None (results in AttributeError)."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        # Mock fetch_temporal_history to return None
        with patch(
            "zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy.fetch_temporal_history",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = None

            with pytest.raises(AttributeError):
                await handler.execute(node_ids=["activity#1"])

            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_exception(self):
        """Test execute method when an exception occurs."""
        handler = TemporalHistoryStrategyHandler(
            reference_workflow_id="workflow-123",
            reference_workflow_run_id="run-456",
        )

        mock_history = Mock(spec=WorkflowHistory)

        # Mock fetch_temporal_history and extract_node_payload to raise exception
        with patch(
            "zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy.fetch_temporal_history",
            new_callable=AsyncMock,
        ) as mock_fetch:
            with patch(
                "zamp_public_workflow_sdk.simulation.strategies.temporal_history_strategy.extract_node_payload",
                new_callable=AsyncMock,
            ) as mock_extract:
                mock_fetch.return_value = mock_history
                mock_extract.side_effect = Exception("Test error")

                with pytest.raises(Exception, match="Test error"):
                    await handler.execute(
                        node_ids=["activity#1"],
                    )

    @pytest.mark.asyncio
    async def test_fetch_temporal_history_success(self):
        """Test fetch_temporal_history with successful fetch."""
        mock_workflow_history = Mock(spec=WorkflowHistory)

        # Patch at the import location in the function
        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_child_workflow", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_workflow_history

            result = await fetch_temporal_history(
                node_ids=["activity#1"],
                workflow_id="workflow-123",
                run_id="run-456",
            )

            assert result == mock_workflow_history
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][0] == "FetchTemporalWorkflowHistoryWorkflow"
            assert call_args[1]["result_type"] is not None

    @pytest.mark.asyncio
    async def test_fetch_temporal_history_with_custom_ids(self):
        """Test fetch_temporal_history with custom workflow_id and run_id."""
        mock_workflow_history = Mock(spec=WorkflowHistory)

        # Patch at the import location in the function
        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_child_workflow", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_workflow_history

            result = await fetch_temporal_history(
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
        """Test fetch_temporal_history with exception."""
        # Patch at the import location in the function
        with patch(
            "zamp_public_workflow_sdk.actions_hub.ActionsHub.execute_child_workflow", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = Exception("Fetch failed")

            with pytest.raises(Exception, match="Failed to fetch temporal history"):
                await fetch_temporal_history(
                    node_ids=["activity#1"],
                    workflow_id="workflow-123",
                    run_id="run-456",
                )

    @pytest.mark.asyncio
    async def test_extract_node_output_main_workflow_only(self):
        """Test extract_node_payload with only main workflow nodes."""
        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_nodes_data_encoded.return_value = {
            "activity#1": NodePayload(
                node_id="activity#1",
                input_payload={"input": "input-activity#1"},
                output_payload={"output": "output-activity#1"},
            ),
            "activity#2": NodePayload(
                node_id="activity#2",
                input_payload={"input": "input-activity#2"},
                output_payload={"output": "output-activity#2"},
            ),
        }

        # Set the cached history
        workflow_histories_map = {"main_workflow": mock_history}

        result = await extract_node_payload(
            node_ids=["activity#1", "activity#2"],
            workflow_histories_map=workflow_histories_map,
        )

        assert "activity#1" in result
        assert "activity#2" in result
        assert result["activity#1"].input_payload == {"input": "input-activity#1"}
        assert result["activity#1"].output_payload == {"output": "output-activity#1"}
        assert result["activity#2"].input_payload == {"input": "input-activity#2"}
        assert result["activity#2"].output_payload == {"output": "output-activity#2"}
        mock_history.get_nodes_data_encoded.assert_called_once_with(target_node_ids=["activity#1", "activity#2"])

    @pytest.mark.asyncio
    async def test_extract_node_output_with_child_workflow(self):
        """Test extract_node_payload with child workflow nodes."""
        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_nodes_data_encoded.return_value = {
            "activity#1": NodePayload(
                node_id="activity#1",
                input_payload={"input": "main-input"},
                output_payload={"output": "main-output"},
            ),
        }

        # Set the cached history
        workflow_histories_map = {"main_workflow": mock_history}

        # Mock extract_child_workflow_node_payloads
        with patch(
            "zamp_public_workflow_sdk.simulation.helper.extract_child_workflow_node_payloads", new_callable=AsyncMock
        ) as mock_child:
            mock_child.return_value = {
                "Child#1.activity#1": NodePayload(
                    node_id="Child#1.activity#1",
                    input_payload=None,
                    output_payload="child-output",
                )
            }

            result = await extract_node_payload(
                node_ids=["activity#1", "Child#1.activity#1"],
                workflow_histories_map=workflow_histories_map,
            )

            assert "activity#1" in result
            assert "Child#1.activity#1" in result
            child_output = result["Child#1.activity#1"].output_payload
            assert child_output == "child-output"

    @pytest.mark.asyncio
    async def test_extract_node_output_with_exception(self):
        """Test extract_node_payload when an exception occurs."""
        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_nodes_data_encoded.side_effect = Exception("Extract error")

        # Set the cached history
        workflow_histories_map = {"main_workflow": mock_history}

        with pytest.raises(Exception):
            await extract_node_payload(
                node_ids=["activity#1"],
                workflow_histories_map=workflow_histories_map,
            )

    def test_extract_main_workflow_node_outputs(self):
        """Test extract_main_workflow_node_payloads method."""
        mock_history = Mock(spec=WorkflowHistory)
        mock_history.get_nodes_data_encoded.return_value = {
            "activity#1": NodePayload(
                node_id="activity#1",
                input_payload={"input": "input-activity#1"},
                output_payload={"output": "output-activity#1"},
            ),
            "activity#2": NodePayload(
                node_id="activity#2",
                input_payload={"input": "input-activity#2"},
                output_payload={"output": "output-activity#2"},
            ),
        }

        result = extract_main_workflow_node_payloads(
            temporal_history=mock_history,
            node_ids=["activity#1", "activity#2"],
        )

        assert "activity#1" in result
        assert "activity#2" in result
        assert result["activity#1"].input_payload == {"input": "input-activity#1"}
        assert result["activity#1"].output_payload == {"output": "output-activity#1"}
        assert result["activity#2"].input_payload == {"input": "input-activity#2"}
        assert result["activity#2"].output_payload == {"output": "output-activity#2"}
        mock_history.get_nodes_data_encoded.assert_called_once_with(target_node_ids=["activity#1", "activity#2"])

    @pytest.mark.asyncio
    async def test_extract_child_workflow_node_outputs_success(self):
        """Test extract_child_workflow_node_payloads with successful extraction."""
        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_child_history = Mock(spec=WorkflowHistory)
        mock_child_history.workflow_id = "child-workflow-id"
        mock_child_history.run_id = "child-run-id"

        # Mock child history node data (encoded format)
        mock_node_data = {
            "Child#1.activity#1": NodePayload(
                node_id="Child#1.activity#1",
                input_payload={"input": "child-input"},
                output_payload={"result": "child-result"},
            )
        }
        mock_child_history.get_nodes_data_encoded.return_value = mock_node_data

        # Mock fetch_nested_child_workflow_history
        workflow_histories_map = {}
        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_nested_child_workflow_history", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_child_history

            result = await extract_child_workflow_node_payloads(
                parent_history=mock_parent_history,
                child_workflow_id="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed=None,
                workflow_histories_map=workflow_histories_map,
            )

            assert "Child#1.activity#1" in result
            assert result["Child#1.activity#1"].input_payload == {"input": "child-input"}
            assert result["Child#1.activity#1"].output_payload == {"result": "child-result"}

    @pytest.mark.asyncio
    async def test_extract_child_workflow_node_outputs_not_found(self):
        """Test extract_child_workflow_node_payloads when child history is not found."""
        mock_parent_history = Mock(spec=WorkflowHistory)

        # Mock fetch_nested_child_workflow_history to return None
        workflow_histories_map = {}
        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_nested_child_workflow_history", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = None

            # When child_history is None, accessing child_history.run_id raises AttributeError
            with pytest.raises(AttributeError, match="run_id"):
                await extract_child_workflow_node_payloads(
                    parent_history=mock_parent_history,
                    child_workflow_id="Child#1",
                    node_ids=["Child#1.activity#1", "Child#1.activity#2"],
                    workflow_nodes_needed=None,
                    workflow_histories_map=workflow_histories_map,
                )

    @pytest.mark.asyncio
    async def test_extract_child_workflow_node_outputs_missing_node(self):
        """Test extract_child_workflow_node_payloads when node is missing in child history."""
        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_child_history = Mock(spec=WorkflowHistory)
        mock_child_history.workflow_id = "child-workflow-id"
        mock_child_history.run_id = "child-run-id"

        # Mock child history with empty node data
        mock_child_history.get_nodes_data_encoded.return_value = {}

        # Mock fetch_nested_child_workflow_history
        workflow_histories_map = {}
        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_nested_child_workflow_history", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_child_history

            result = await extract_child_workflow_node_payloads(
                parent_history=mock_parent_history,
                child_workflow_id="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed=None,
                workflow_histories_map=workflow_histories_map,
            )

            assert "Child#1.activity#1" in result

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_single_level(self):
        """Test fetch_nested_child_workflow_history with single level nesting."""
        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_parent_history.get_child_workflow_workflow_id_run_id.return_value = (
            "child-workflow-id",
            "child-run-id",
        )

        mock_child_history = Mock(spec=WorkflowHistory)

        # Mock fetch_temporal_history
        workflow_histories_map = {}
        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_temporal_history", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_child_history

            result = await fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed={},
                workflow_histories_map=workflow_histories_map,
            )

            assert result == mock_child_history
            mock_parent_history.get_child_workflow_workflow_id_run_id.assert_called_once_with(node_id="Child#1")

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_with_cache(self):
        """Test fetch_nested_child_workflow_history using cached history."""
        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_cached_history = Mock(spec=WorkflowHistory)

        # Use cached history
        workflow_histories_map = {"Child#1": mock_cached_history}

        result = await fetch_nested_child_workflow_history(
            parent_workflow_history=mock_parent_history,
            full_child_path="Child#1",
            node_ids=["Child#1.activity#1"],
            workflow_nodes_needed={},
            workflow_histories_map=workflow_histories_map,
        )

        assert result == mock_cached_history

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_no_workflow_id(self):
        """Test fetch_nested_child_workflow_history when workflow_id not found."""
        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_parent_history.get_child_workflow_workflow_id_run_id.side_effect = ValueError(
            "No node data found for child workflow with node_id=Child#1"
        )
        workflow_histories_map = {}

        with pytest.raises(Exception, match="Failed to get workflow_id and run_id"):
            await fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed={},
                workflow_histories_map=workflow_histories_map,
            )

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_nested_levels(self):
        """Test fetch_nested_child_workflow_history with multiple nested levels."""
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

        # Mock fetch_temporal_history
        workflow_histories_map = {}
        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_temporal_history", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = [mock_intermediate_history, mock_final_history]

            result = await fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Parent#1.Child#1",
                node_ids=["Parent#1.Child#1.activity#1"],
                workflow_nodes_needed={},
                workflow_histories_map=workflow_histories_map,
            )

            assert result == mock_final_history
            assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_fetch_fails(self):
        """Test fetch_nested_child_workflow_history when fetch fails."""
        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_parent_history.get_child_workflow_workflow_id_run_id.return_value = (
            "child-workflow-id",
            "child-run-id",
        )

        # Mock fetch_temporal_history to return None
        workflow_histories_map = {}
        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_temporal_history", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = None

            result = await fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed={},
                workflow_histories_map=workflow_histories_map,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_with_workflow_nodes_needed(self):
        """Test fetch_nested_child_workflow_history with pre-collected workflow nodes."""
        mock_parent_history = Mock(spec=WorkflowHistory)
        mock_parent_history.get_child_workflow_workflow_id_run_id.return_value = (
            "child-workflow-id",
            "child-run-id",
        )

        mock_child_history = Mock(spec=WorkflowHistory)

        workflow_nodes_needed = {"Child#1": ["Child#1.activity#1", "Child#1.activity#2"]}
        workflow_histories_map = {}

        # Mock fetch_temporal_history
        with patch(
            "zamp_public_workflow_sdk.simulation.helper.fetch_temporal_history", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_child_history

            result = await fetch_nested_child_workflow_history(
                parent_workflow_history=mock_parent_history,
                full_child_path="Child#1",
                node_ids=["Child#1.activity#1"],
                workflow_nodes_needed=workflow_nodes_needed,
                workflow_histories_map=workflow_histories_map,
            )

            assert result == mock_child_history
            # Check that it used workflow_nodes_needed
            call_args = mock_fetch.call_args
            assert call_args[1]["node_ids"] == ["Child#1.activity#1", "Child#1.activity#2"]

    def test_get_workflow_path_from_node(self):
        """Test get_workflow_path_from_node method."""
        # Test normal case
        result = get_workflow_path_from_node(
            node_id="Parent#1.Child#1.activity#1",
            child_workflow_id="Child#1",
        )
        assert result == "Parent#1.Child#1"

        # Test when child_workflow_id is at the start
        result = get_workflow_path_from_node(
            node_id="Child#1.activity#1",
            child_workflow_id="Child#1",
        )
        assert result == "Child#1"

        # Test when child_workflow_id is not found
        result = get_workflow_path_from_node(
            node_id="Parent#1.activity#1",
            child_workflow_id="Child#1",
        )
        assert result == "Child#1"

    def test_collect_nodes_per_workflow(self):
        """Test collect_nodes_per_workflow method."""
        # Test with simple nodes
        result = collect_nodes_per_workflow(["Parent#1.query#1", "Parent#1.Child#1.activity#1"])

        assert "Parent#1" in result
        assert "Parent#1.query#1" in result["Parent#1"]
        assert "Parent#1.Child#1" in result["Parent#1"]
        assert "Parent#1.Child#1" in result
        assert "Parent#1.Child#1.activity#1" in result["Parent#1.Child#1"]

        # Test with single-level nodes
        result = collect_nodes_per_workflow(["activity#1", "activity#2"])
        # Single-level nodes don't create any workflow entries
        assert result == {}

        # Test with multiple nested levels
        result = collect_nodes_per_workflow(["Parent#1.Child#1.GrandChild#1.activity#1"])
        assert "Parent#1" in result
        assert "Parent#1.Child#1" in result
        assert "Parent#1.Child#1.GrandChild#1" in result

    def test_group_nodes_by_parent_workflow(self):
        """Test group_nodes_by_parent_workflow method."""
        # Test with single-level nodes
        result = group_nodes_by_parent_workflow(["activity#1", "activity#2"])
        assert result == {MAIN_WORKFLOW_IDENTIFIER: ["activity#1", "activity#2"]}

        # Test with child workflow nodes
        result = group_nodes_by_parent_workflow(["activity#1", "Child#1.activity#1", "Child#1.activity#2"])
        assert MAIN_WORKFLOW_IDENTIFIER in result
        assert "Child#1" in result
        assert result[MAIN_WORKFLOW_IDENTIFIER] == ["activity#1"]
        assert result["Child#1"] == ["Child#1.activity#1", "Child#1.activity#2"]

        # Test with nested child workflows
        result = group_nodes_by_parent_workflow(["Parent#1.Child#1.activity#1", "Parent#1.activity#1"])
        assert "Parent#1.Child#1" in result
        assert "Parent#1" in result
        assert result["Parent#1.Child#1"] == ["Parent#1.Child#1.activity#1"]
        assert result["Parent#1"] == ["Parent#1.activity#1"]

        # Test with deeply nested workflows
        result = group_nodes_by_parent_workflow(["Parent#1.Child#1.GrandChild#1.activity#1"])
        assert result == {"Parent#1.Child#1.GrandChild#1": ["Parent#1.Child#1.GrandChild#1.activity#1"]}
