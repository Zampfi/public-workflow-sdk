"""
Unit tests for simulation validator workflow.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from zamp_public_workflow_sdk.simulation.workflows.simulation_validator_workflow import (
    SimulationValidatorWorkflow,
    MAIN_WORKFLOW_IDENTIFIER,
)
from zamp_public_workflow_sdk.simulation.models.simulation_validation import (
    SimulationValidatorInput,
    SimulationValidatorOutput,
    NodeComparison,
)
from zamp_public_workflow_sdk.simulation.models import (
    SimulationConfig,
    NodeMockConfig,
    NodeStrategy,
    SimulationStrategyConfig,
    StrategyType,
    CustomOutputConfig,
)


class TestSimulationValidatorWorkflow:
    """Test SimulationValidatorWorkflow class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.workflow = SimulationValidatorWorkflow()

        # Create test data
        self.mock_config = NodeMockConfig(
            node_strategies=[
                NodeStrategy(
                    strategy=SimulationStrategyConfig(
                        type=StrategyType.CUSTOM_OUTPUT,
                        config=CustomOutputConfig(output_value="test"),
                    ),
                    nodes=["activity#1", "Child#1.activity#2"],
                )
            ]
        )
        self.simulation_config = SimulationConfig(mock_config=self.mock_config)

        self.validator_input = SimulationValidatorInput(
            simulation_workflow_id="sim-workflow-123",
            simulation_workflow_run_id="sim-run-456",
            golden_workflow_id="golden-workflow-789",
            golden_run_id="golden-run-012",
            simulation_config=self.simulation_config,
        )

    def test_init(self):
        """Test workflow initialization."""
        workflow = SimulationValidatorWorkflow()
        assert workflow.reference_workflow_histories == {}
        assert workflow.golden_workflow_histories == {}

    def test_get_mocked_nodes_valid_config(self):
        """Test extracting mocked nodes from valid simulation config."""
        mocked_nodes = self.workflow._get_mocked_nodes(self.simulation_config)

        assert mocked_nodes == {"activity#1", "Child#1.activity#2"}

    def test_get_mocked_nodes_empty_config(self):
        """Test extracting mocked nodes from empty simulation config."""
        empty_mock_config = NodeMockConfig(node_strategies=[])
        empty_config = SimulationConfig(mock_config=empty_mock_config)
        mocked_nodes = self.workflow._get_mocked_nodes(empty_config)

        assert mocked_nodes == set()

    def test_get_mocked_nodes_none_config(self):
        """Test extracting mocked nodes from None simulation config."""
        mocked_nodes = self.workflow._get_mocked_nodes(None)

        assert mocked_nodes == set()

    def test_get_mocked_nodes_no_node_strategies(self):
        """Test extracting mocked nodes when no node strategies exist."""
        mock_config = NodeMockConfig(node_strategies=[])
        sim_config = SimulationConfig(mock_config=mock_config)
        mocked_nodes = self.workflow._get_mocked_nodes(sim_config)

        assert mocked_nodes == set()

    def test_simulation_validator_output_defaults(self):
        """Test that SimulationValidatorOutput has correct default values."""
        output = SimulationValidatorOutput(
            total_nodes_compared=0,
            mocked_nodes_count=0,
            matching_nodes_count=0,
            mismatched_nodes_count=0,
            mismatched_node_ids=None,
            comparison_error_nodes_count=0,
            comparison_error_node_ids=None,
            nodes_missing_in_simulation_workflow=None,
            nodes_missing_in_golden_workflow=None,
            comparisons=[],
            validation_passed=True,
        )

        assert output.total_nodes_compared == 0
        assert output.mocked_nodes_count == 0
        assert output.matching_nodes_count == 0
        assert output.mismatched_nodes_count == 0
        assert output.mismatched_node_ids is None
        assert output.comparison_error_nodes_count == 0
        assert output.comparison_error_node_ids is None
        assert output.nodes_missing_in_simulation_workflow is None
        assert output.nodes_missing_in_golden_workflow is None
        assert output.comparisons == []
        assert output.validation_passed is True

    def test_build_output_matching_nodes(self):
        """Test building output with matching nodes."""
        comparisons = [
            NodeComparison(
                node_id="activity#1",
                is_mocked=False,
                inputs_match=True,
                outputs_match=True,
            ),
            NodeComparison(
                node_id="activity#2",
                is_mocked=False,
                inputs_match=True,
                outputs_match=True,
            ),
        ]

        output = self.workflow._build_output(comparisons)

        assert output.total_nodes_compared == 2
        assert output.mocked_nodes_count == 2
        assert output.matching_nodes_count == 2
        assert output.mismatched_nodes_count == 0
        assert output.mismatched_node_ids is None
        assert output.comparison_error_nodes_count == 0
        assert output.comparison_error_node_ids is None
        assert output.nodes_missing_in_simulation_workflow is None
        assert output.nodes_missing_in_golden_workflow is None
        assert output.validation_passed is True

    def test_build_output_mismatched_nodes(self):
        """Test building output with mismatched nodes."""
        comparisons = [
            NodeComparison(
                node_id="activity#1",
                is_mocked=False,
                inputs_match=True,
                outputs_match=True,
            ),
            NodeComparison(
                node_id="activity#2",
                is_mocked=False,
                inputs_match=False,
                outputs_match=False,
                difference={"values_changed": {"root['param']": {"new_value": "value1", "old_value": "value2"}}},
                output_difference={
                    "values_changed": {"root['result']": {"new_value": "success1", "old_value": "success2"}}
                },
            ),
        ]

        output = self.workflow._build_output(comparisons)

        assert output.total_nodes_compared == 2
        assert output.mocked_nodes_count == 2
        assert output.matching_nodes_count == 1
        assert output.mismatched_nodes_count == 1
        assert output.mismatched_node_ids == ["activity#2"]
        assert output.comparison_error_nodes_count == 0
        assert output.comparison_error_node_ids is None
        assert output.nodes_missing_in_simulation_workflow is None
        assert output.nodes_missing_in_golden_workflow is None
        assert output.validation_passed is False

    def test_build_output_error_nodes(self):
        """Test building output with error nodes."""
        comparisons = [
            NodeComparison(
                node_id="activity#1",
                is_mocked=False,
                inputs_match=True,
                outputs_match=True,
            ),
            NodeComparison(
                node_id="activity#2",
                is_mocked=False,
                error="Node not found in simulation workflow",
            ),
        ]

        output = self.workflow._build_output(comparisons)

        assert output.total_nodes_compared == 2
        assert output.mocked_nodes_count == 2
        assert output.matching_nodes_count == 1
        assert output.mismatched_nodes_count == 0
        assert output.mismatched_node_ids is None
        assert output.comparison_error_nodes_count == 1
        assert output.comparison_error_node_ids == ["activity#2"]
        assert output.nodes_missing_in_simulation_workflow == ["activity#2"]
        assert output.nodes_missing_in_golden_workflow is None
        assert output.validation_passed is False

    def test_build_output_missing_nodes_in_golden(self):
        """Test building output with nodes missing in golden workflow."""
        comparisons = [
            NodeComparison(
                node_id="activity#1",
                is_mocked=False,
                inputs_match=True,
                outputs_match=True,
            ),
            NodeComparison(
                node_id="activity#2",
                is_mocked=False,
                error="Node not found in golden workflow",
            ),
        ]

        output = self.workflow._build_output(comparisons)

        assert output.total_nodes_compared == 2
        assert output.mocked_nodes_count == 2
        assert output.matching_nodes_count == 1
        assert output.mismatched_nodes_count == 0
        assert output.mismatched_node_ids is None
        assert output.comparison_error_nodes_count == 1
        assert output.comparison_error_node_ids == ["activity#2"]
        assert output.nodes_missing_in_simulation_workflow is None
        assert output.nodes_missing_in_golden_workflow == ["activity#2"]
        assert output.validation_passed is False

    def test_create_error_comparison(self):
        """Test creating error comparison."""
        comparison = self.workflow._create_error_comparison(
            node_id="activity#1", is_mocked=True, error="Test error message"
        )

        assert comparison.node_id == "activity#1"
        assert comparison.is_mocked is True
        assert comparison.inputs_match is None
        assert comparison.outputs_match is None
        assert comparison.error == "Test error message"

    def test_group_nodes_by_parent_workflow_main_workflow(self):
        """Test grouping nodes by parent workflow for main workflow nodes."""
        node_ids = ["activity#1", "activity#2"]
        groups = self.workflow._group_nodes_by_parent_workflow(node_ids)

        assert groups == {MAIN_WORKFLOW_IDENTIFIER: ["activity#1", "activity#2"]}

    def test_group_nodes_by_parent_workflow_child_workflow(self):
        """Test grouping nodes by parent workflow for child workflow nodes."""
        node_ids = ["Child#1.activity#1", "Child#1.activity#2"]
        groups = self.workflow._group_nodes_by_parent_workflow(node_ids)

        assert groups == {"Child#1": ["Child#1.activity#1", "Child#1.activity#2"]}

    def test_group_nodes_by_parent_workflow_nested_workflow(self):
        """Test grouping nodes by parent workflow for nested workflow nodes."""
        node_ids = ["Parent#1.Child#1.activity#1", "Parent#1.Child#1.activity#2"]
        groups = self.workflow._group_nodes_by_parent_workflow(node_ids)

        assert groups == {"Parent#1.Child#1": ["Parent#1.Child#1.activity#1", "Parent#1.Child#1.activity#2"]}

    def test_group_nodes_by_parent_workflow_mixed(self):
        """Test grouping nodes by parent workflow with mixed node types."""
        node_ids = ["activity#1", "Child#1.activity#2", "Parent#1.Child#1.activity#3"]
        groups = self.workflow._group_nodes_by_parent_workflow(node_ids)

        expected = {
            MAIN_WORKFLOW_IDENTIFIER: ["activity#1"],
            "Child#1": ["Child#1.activity#2"],
            "Parent#1.Child#1": ["Parent#1.Child#1.activity#3"],
        }
        assert groups == expected

    def test_get_workflow_path_from_node_simple(self):
        """Test getting workflow path from simple node ID."""
        path = self.workflow._get_workflow_path_from_node("Child#1.activity#1", "Child#1")

        assert path == "Child#1"

    def test_get_workflow_path_from_node_nested(self):
        """Test getting workflow path from nested node ID."""
        path = self.workflow._get_workflow_path_from_node("Parent#1.Child#1.activity#1", "Child#1")

        assert path == "Parent#1.Child#1"

    def test_get_workflow_path_from_node_not_found(self):
        """Test getting workflow path when child workflow ID not found."""
        path = self.workflow._get_workflow_path_from_node("Parent#1.activity#1", "Child#1")

        assert path == "Parent#1"

    @pytest.mark.asyncio
    async def test_compare_node_matching_inputs_outputs(self):
        """Test comparing node with matching inputs and outputs."""
        # Mock node data
        reference_node = Mock()
        reference_node.input_payload = {"param": "value"}
        reference_node.output_payload = {"result": "success"}

        golden_node = Mock()
        golden_node.input_payload = {"param": "value"}
        golden_node.output_payload = {"result": "success"}

        reference_nodes = {"activity#1": reference_node}
        golden_nodes = {"activity#1": golden_node}
        mocked_nodes = {"activity#1"}

        comparison = await self.workflow._compare_node("activity#1", mocked_nodes, reference_nodes, golden_nodes)

        assert comparison.node_id == "activity#1"
        assert comparison.is_mocked is True
        assert comparison.inputs_match is True
        assert comparison.outputs_match is True
        assert comparison.actual_input == {"param": "value"}
        assert comparison.expected_input == {"param": "value"}
        assert comparison.actual_output == {"result": "success"}
        assert comparison.expected_output == {"result": "success"}
        assert comparison.difference is None
        assert comparison.output_difference is None
        assert comparison.error is None

    @pytest.mark.asyncio
    async def test_compare_node_mismatched_inputs_outputs(self):
        """Test comparing node with mismatched inputs and outputs."""
        # Mock node data
        reference_node = Mock()
        reference_node.input_payload = {"param": "value1"}
        reference_node.output_payload = {"result": "success1"}

        golden_node = Mock()
        golden_node.input_payload = {"param": "value2"}
        golden_node.output_payload = {"result": "success2"}

        reference_nodes = {"activity#1": reference_node}
        golden_nodes = {"activity#1": golden_node}
        mocked_nodes = {"activity#1"}

        comparison = await self.workflow._compare_node("activity#1", mocked_nodes, reference_nodes, golden_nodes)

        assert comparison.node_id == "activity#1"
        assert comparison.is_mocked is True
        assert comparison.inputs_match is False
        assert comparison.outputs_match is False
        assert comparison.actual_input == {"param": "value1"}
        assert comparison.expected_input == {"param": "value2"}
        assert comparison.actual_output == {"result": "success1"}
        assert comparison.expected_output == {"result": "success2"}
        assert comparison.difference is not None
        assert comparison.output_difference is not None
        assert comparison.error is None

    @pytest.mark.asyncio
    async def test_compare_node_reference_node_not_found(self):
        """Test comparing node when reference node is not found."""
        reference_nodes = {}
        golden_nodes = {"activity#1": Mock()}
        mocked_nodes = {"activity#1"}

        comparison = await self.workflow._compare_node("activity#1", mocked_nodes, reference_nodes, golden_nodes)

        assert comparison.node_id == "activity#1"
        assert comparison.is_mocked is True
        assert comparison.inputs_match is None
        assert comparison.outputs_match is None
        assert comparison.error == "Node not found in simulation workflow"

    @pytest.mark.asyncio
    async def test_compare_node_golden_node_not_found(self):
        """Test comparing node when golden node is not found."""
        reference_nodes = {"activity#1": Mock()}
        golden_nodes = {}
        mocked_nodes = {"activity#1"}

        comparison = await self.workflow._compare_node("activity#1", mocked_nodes, reference_nodes, golden_nodes)

        assert comparison.node_id == "activity#1"
        assert comparison.is_mocked is True
        assert comparison.inputs_match is None
        assert comparison.outputs_match is None
        assert comparison.error == "Node not found in golden workflow"

    @pytest.mark.asyncio
    async def test_compare_node_exception(self):
        """Test comparing node when exception occurs."""
        reference_node = Mock()
        reference_node.input_payload = {"param": "value"}
        reference_node.output_payload = {"result": "success"}

        golden_node = Mock()
        golden_node.input_payload = {"param": "value"}
        golden_node.output_payload = {"result": "success"}

        reference_nodes = {"activity#1": reference_node}
        golden_nodes = {"activity#1": golden_node}
        mocked_nodes = {"activity#1"}

        # Mock DeepDiff to raise an exception
        with patch(
            "zamp_public_workflow_sdk.simulation.workflows.simulation_validator_workflow.DeepDiff"
        ) as mock_deepdiff:
            mock_deepdiff.side_effect = Exception("Test exception")

            comparison = await self.workflow._compare_node("activity#1", mocked_nodes, reference_nodes, golden_nodes)

            assert comparison.node_id == "activity#1"
            assert comparison.is_mocked is True
            assert comparison.inputs_match is None
            assert comparison.outputs_match is None
            assert comparison.error == "Comparison error: Test exception"

    @pytest.mark.asyncio
    async def test_compare_main_workflow_nodes(self):
        """Test comparing main workflow nodes."""
        # Mock workflow histories
        reference_history = Mock()
        reference_history.get_nodes_data.return_value = {
            "activity#1": Mock(input_payload={"param": "value"}, output_payload={"result": "success"}),
            "activity#2": Mock(input_payload={"param": "value"}, output_payload={"result": "success"}),
        }

        golden_history = Mock()
        golden_history.get_nodes_data.return_value = {
            "activity#1": Mock(input_payload={"param": "value"}, output_payload={"result": "success"}),
            "activity#2": Mock(input_payload={"param": "value"}, output_payload={"result": "success"}),
        }

        self.workflow.reference_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = reference_history
        self.workflow.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = golden_history

        node_ids = ["activity#1", "activity#2"]
        mocked_nodes = {"activity#1", "activity#2"}

        comparisons = await self.workflow._compare_main_workflow_nodes(node_ids, mocked_nodes)

        assert len(comparisons) == 2
        assert comparisons[0].node_id == "activity#1"
        assert comparisons[1].node_id == "activity#2"

    @pytest.mark.asyncio
    async def test_fetch_workflow_history_success(self):
        """Test successful workflow history fetching."""
        mock_history = Mock()
        mock_history.events = ["event1", "event2"]

        with patch(
            "zamp_public_workflow_sdk.simulation.workflows.simulation_validator_workflow.ActionsHub"
        ) as mock_actions_hub:
            mock_actions_hub.execute_child_workflow = AsyncMock(return_value=mock_history)

            result = await self.workflow._fetch_workflow_history(
                workflow_id="test-workflow", run_id="test-run", description="test"
            )

            assert result == mock_history
            mock_actions_hub.execute_child_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_workflow_history_failure(self):
        """Test workflow history fetching failure."""
        with patch(
            "zamp_public_workflow_sdk.simulation.workflows.simulation_validator_workflow.ActionsHub"
        ) as mock_actions_hub:
            mock_actions_hub.execute_child_workflow = AsyncMock(side_effect=Exception("Test error"))

            with pytest.raises(Exception, match="Test error"):
                await self.workflow._fetch_workflow_history(
                    workflow_id="test-workflow", run_id="test-run", description="test"
                )

    @pytest.mark.asyncio
    async def test_fetch_and_cache_main_workflows(self):
        """Test fetching and caching main workflows."""
        mock_reference_history = Mock()
        mock_golden_history = Mock()

        with patch.object(self.workflow, "_fetch_workflow_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [mock_reference_history, mock_golden_history]

            await self.workflow._fetch_and_cache_main_workflows(self.validator_input)

            assert self.workflow.reference_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] == mock_reference_history
            assert self.workflow.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] == mock_golden_history
            assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_compare_all_nodes_main_workflow_only(self):
        """Test comparing all nodes with only main workflow nodes."""
        mocked_nodes = {"activity#1", "activity#2"}

        with patch.object(self.workflow, "_compare_main_workflow_nodes", new_callable=AsyncMock) as mock_compare_main:
            mock_compare_main.return_value = [
                NodeComparison(node_id="activity#1", is_mocked=True),
                NodeComparison(node_id="activity#2", is_mocked=True),
            ]

            comparisons = await self.workflow._compare_all_nodes(mocked_nodes)

            assert len(comparisons) == 2
            # Check that both nodes are present (order may vary due to sorting)
            node_ids = [comp.node_id for comp in comparisons]
            assert "activity#1" in node_ids
            assert "activity#2" in node_ids
            # Check that the method was called with sorted node IDs
            mock_compare_main.assert_called_once()
            call_args = mock_compare_main.call_args[0]
            assert set(call_args[0]) == {"activity#1", "activity#2"}
            assert call_args[1] == mocked_nodes

    @pytest.mark.asyncio
    async def test_compare_all_nodes_with_child_workflows(self):
        """Test comparing all nodes with child workflow nodes."""
        mocked_nodes = {"activity#1", "Child#1.activity#2"}

        with patch.object(self.workflow, "_compare_main_workflow_nodes", new_callable=AsyncMock) as mock_compare_main:
            with patch.object(
                self.workflow, "_compare_child_workflow_nodes", new_callable=AsyncMock
            ) as mock_compare_child:
                mock_compare_main.return_value = [NodeComparison(node_id="activity#1", is_mocked=True)]
                mock_compare_child.return_value = [NodeComparison(node_id="Child#1.activity#2", is_mocked=True)]

                comparisons = await self.workflow._compare_all_nodes(mocked_nodes)

                assert len(comparisons) == 2
                # Check that both nodes are present (order may vary due to grouping)
                node_ids = [comp.node_id for comp in comparisons]
                assert "activity#1" in node_ids
                assert "Child#1.activity#2" in node_ids
                mock_compare_main.assert_called_once_with(["activity#1"], mocked_nodes)
                mock_compare_child.assert_called_once_with("Child#1", ["Child#1.activity#2"], mocked_nodes)

    @pytest.mark.asyncio
    async def test_execute_no_mocked_nodes(self):
        """Test execute method when no mocked nodes are found."""
        empty_mock_config = NodeMockConfig(node_strategies=[])
        empty_config = SimulationConfig(mock_config=empty_mock_config)
        input_data = SimulationValidatorInput(
            simulation_workflow_id="sim-workflow-123",
            simulation_workflow_run_id="sim-run-456",
            golden_workflow_id="golden-workflow-789",
            golden_run_id="golden-run-012",
            simulation_config=empty_config,
        )

        result = await self.workflow.execute(input_data)

        assert result.total_nodes_compared == 0
        assert result.validation_passed is True

    @pytest.mark.asyncio
    async def test_execute_with_mocked_nodes(self):
        """Test execute method with mocked nodes."""
        with patch.object(self.workflow, "_fetch_and_cache_main_workflows", new_callable=AsyncMock) as mock_fetch:
            with patch.object(self.workflow, "_compare_all_nodes", new_callable=AsyncMock) as mock_compare:
                mock_compare.return_value = [
                    NodeComparison(
                        node_id="activity#1",
                        is_mocked=True,
                        inputs_match=True,
                        outputs_match=True,
                    )
                ]

                result = await self.workflow.execute(self.validator_input)

                assert result.total_nodes_compared == 1
                assert result.validation_passed is True
                mock_fetch.assert_called_once_with(self.validator_input)
                mock_compare.assert_called_once_with({"activity#1", "Child#1.activity#2"})

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_success(self):
        """Test successful nested child workflow history fetching."""
        # Mock parent workflow history
        parent_history = Mock()
        parent_history.get_child_workflow_workflow_id_run_id.return_value = ("child-workflow-id", "child-run-id")

        # Mock child workflow history
        child_history = Mock()

        with patch.object(self.workflow, "_fetch_workflow_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = child_history

            result = await self.workflow._fetch_nested_child_workflow_history(
                parent_workflow_history=parent_history, full_child_path="Child#1", is_reference=True
            )

            assert result == child_history
            assert self.workflow.reference_workflow_histories["Child#1"] == child_history
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_cached(self):
        """Test nested child workflow history fetching with cached result."""
        # Mock cached history
        cached_history = Mock()
        self.workflow.reference_workflow_histories["Child#1"] = cached_history

        parent_history = Mock()

        result = await self.workflow._fetch_nested_child_workflow_history(
            parent_workflow_history=parent_history, full_child_path="Child#1", is_reference=True
        )

        assert result == cached_history

    @pytest.mark.asyncio
    async def test_fetch_nested_child_workflow_history_error(self):
        """Test nested child workflow history fetching with error."""
        parent_history = Mock()
        parent_history.get_child_workflow_workflow_id_run_id.side_effect = ValueError("Child workflow not found")

        with pytest.raises(Exception, match="Failed to get workflow_id and run_id for child workflow"):
            await self.workflow._fetch_nested_child_workflow_history(
                parent_workflow_history=parent_history, full_child_path="Child#1", is_reference=True
            )

    @pytest.mark.asyncio
    async def test_compare_child_workflow_nodes_success(self):
        """Test successful child workflow node comparison."""
        # Mock main workflow histories
        main_reference_history = Mock()
        main_golden_history = Mock()
        self.workflow.reference_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = main_reference_history
        self.workflow.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = main_golden_history

        # Mock child workflow histories
        child_reference_history = Mock()
        child_reference_history.get_nodes_data.return_value = {
            "Child#1.activity#1": Mock(input_payload={"param": "value"}, output_payload={"result": "success"})
        }

        child_golden_history = Mock()
        child_golden_history.get_nodes_data.return_value = {
            "Child#1.activity#1": Mock(input_payload={"param": "value"}, output_payload={"result": "success"})
        }

        with patch.object(self.workflow, "_fetch_nested_child_workflow_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [child_reference_history, child_golden_history]

            comparisons = await self.workflow._compare_child_workflow_nodes(
                parent_workflow_id="Child#1", node_ids=["Child#1.activity#1"], mocked_nodes={"Child#1.activity#1"}
            )

            assert len(comparisons) == 1
            assert comparisons[0].node_id == "Child#1.activity#1"

    @pytest.mark.asyncio
    async def test_compare_child_workflow_nodes_error(self):
        """Test child workflow node comparison with error."""
        # Mock main workflow histories
        main_reference_history = Mock()
        main_golden_history = Mock()
        self.workflow.reference_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = main_reference_history
        self.workflow.golden_workflow_histories[MAIN_WORKFLOW_IDENTIFIER] = main_golden_history

        with patch.object(self.workflow, "_fetch_nested_child_workflow_history", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Failed to fetch child workflow")

            comparisons = await self.workflow._compare_child_workflow_nodes(
                parent_workflow_id="Child#1", node_ids=["Child#1.activity#1"], mocked_nodes={"Child#1.activity#1"}
            )

            assert len(comparisons) == 1
            assert comparisons[0].node_id == "Child#1.activity#1"
            assert comparisons[0].error == "Failed to fetch child workflow history: Failed to fetch child workflow"
