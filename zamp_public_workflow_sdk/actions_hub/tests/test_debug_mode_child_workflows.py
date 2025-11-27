import pytest
from unittest.mock import Mock, patch, AsyncMock

from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode, LogMode


class TestDebugModeChildWorkflows:
    """Test cases for DEBUG mode child workflow execution."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()
        ActionsHub._workflows.clear()
        ActionsHub._workflow_id_to_simulation_map.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()
        ActionsHub._workflows.clear()
        ActionsHub._workflow_id_to_simulation_map.clear()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    async def test_start_child_workflow_in_log_mode_debug_mode(
        self,
        mock_start_child,
        mock_execute_child,
        mock_get_log_mode,
    ):
        """Test _start_child_workflow_in_log_mode in DEBUG mode uses execute_child_workflow."""
        mock_get_log_mode.return_value = LogMode.DEBUG
        mock_execute_child.return_value = "workflow_result"

        result = await ActionsHub._start_child_workflow_in_log_mode(
            workflow_name="TestWorkflow",
            action_name="TestWorkflow",
            node_id="TestWorkflow#1",
            result_type=str,
            args=(),
        )

        # Verify execute_child_workflow was called, not start_child_workflow
        mock_execute_child.assert_called_once_with(
            "TestWorkflow",
            result_type=str,
            args=(),
        )
        mock_start_child.assert_not_called()
        assert result == "workflow_result"

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    async def test_start_child_workflow_in_log_mode_non_debug_mode(
        self,
        mock_start_child,
        mock_execute_child,
        mock_get_log_mode,
    ):
        """Test _start_child_workflow_in_log_mode in non-DEBUG mode uses start_child_workflow."""
        mock_get_log_mode.return_value = LogMode.INFO
        mock_handle = AsyncMock()
        mock_handle.id = "test-workflow-id"
        mock_start_child.return_value = mock_handle

        result = await ActionsHub._start_child_workflow_in_log_mode(
            workflow_name="TestWorkflow",
            action_name="TestWorkflow",
            node_id="TestWorkflow#1",
            result_type=str,
            args=(),
        )

        # Verify start_child_workflow was called, not execute_child_workflow
        mock_start_child.assert_called_once_with(
            "TestWorkflow",
            result_type=str,
            args=(),
        )
        mock_execute_child.assert_not_called()
        assert result == mock_handle

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_start_child_workflow_debug_mode_with_node_id(
        self,
        mock_get_simulation_response,
        mock_start_child,
        mock_execute_child,
        mock_workflow_info,
        mock_get_mode,
        mock_get_log_mode,
    ):
        """Test start_child_workflow in DEBUG mode with node_id generation."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_get_log_mode.return_value = LogMode.DEBUG
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_execute_child.return_value = "workflow_result"
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        result = await ActionsHub.start_child_workflow("TestWorkflow")

        # Verify execute_child_workflow was called
        mock_execute_child.assert_called_once()
        mock_start_child.assert_not_called()
        assert result == "workflow_result"

        # Verify node_id was generated and passed
        call_args = mock_execute_child.call_args
        assert len(call_args[1]["args"]) > 0
        node_id_arg = call_args[1]["args"][0]
        assert "__temporal_node_id" in node_id_arg

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_start_child_workflow_non_debug_mode_with_node_id(
        self,
        mock_get_simulation_response,
        mock_start_child,
        mock_execute_child,
        mock_workflow_info,
        mock_get_mode,
        mock_get_log_mode,
    ):
        """Test start_child_workflow in non-DEBUG mode with node_id generation."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_get_log_mode.return_value = LogMode.INFO
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)

        mock_handle = AsyncMock()
        mock_handle.id = "test-workflow-id"
        mock_start_child.return_value = mock_handle

        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        result = await ActionsHub.start_child_workflow("TestWorkflow")

        # Verify start_child_workflow was called
        mock_start_child.assert_called_once()
        mock_execute_child.assert_not_called()
        assert result == mock_handle

        # Verify node_id was generated and passed
        call_args = mock_start_child.call_args
        assert len(call_args[1]["args"]) > 0
        node_id_arg = call_args[1]["args"][0]
        assert "__temporal_node_id" in node_id_arg

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    async def test_start_child_workflow_skip_node_id_debug_mode(
        self,
        mock_start_child,
        mock_execute_child,
        mock_workflow_info,
        mock_get_mode,
        mock_get_log_mode,
    ):
        """Test start_child_workflow with skip_node_id_gen=True in DEBUG mode."""
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_get_log_mode.return_value = LogMode.DEBUG
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_execute_child.return_value = "workflow_result"

        result = await ActionsHub.start_child_workflow("TestWorkflow", skip_node_id_gen=True)

        # Verify execute_child_workflow was called
        mock_execute_child.assert_called_once()
        mock_start_child.assert_not_called()
        assert result == "workflow_result"

        # Verify no node_id was passed (since we're skipping node_id generation)
        call_args = mock_execute_child.call_args
        assert call_args[1]["args"] == ()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    async def test_start_child_workflow_skip_node_id_non_debug_mode(
        self,
        mock_start_child,
        mock_execute_child,
        mock_workflow_info,
        mock_get_mode,
        mock_get_log_mode,
    ):
        """Test start_child_workflow with skip_node_id_gen=True in non-DEBUG mode."""
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_get_log_mode.return_value = LogMode.INFO
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)

        mock_handle = AsyncMock()
        mock_handle.id = "test-workflow-id"
        mock_start_child.return_value = mock_handle

        result = await ActionsHub.start_child_workflow("TestWorkflow", skip_node_id_gen=True)

        # Verify start_child_workflow was called
        mock_start_child.assert_called_once()
        mock_execute_child.assert_not_called()
        assert result == mock_handle

        # Verify no node_id was passed
        call_args = mock_start_child.call_args
        assert call_args[1]["args"] == ()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_execute_child_workflow_always_waits_for_completion(
        self,
        mock_get_simulation_response,
        mock_execute_child,
        mock_workflow_info,
        mock_get_mode,
        mock_get_log_mode,
    ):
        """Test execute_child_workflow always waits for completion regardless of log mode."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_get_log_mode.return_value = LogMode.INFO  # Non-DEBUG mode
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_execute_child.return_value = "workflow_result"
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        result = await ActionsHub.execute_child_workflow("TestWorkflow")

        # execute_child_workflow should always use execute_child_workflow (waits for completion)
        mock_execute_child.assert_called_once()
        assert result == "workflow_result"

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    async def test_start_child_workflow_in_log_mode_preserves_kwargs(
        self,
        mock_execute_child,
        mock_get_log_mode,
    ):
        """Test that _start_child_workflow_in_log_mode preserves all kwargs."""
        mock_get_log_mode.return_value = LogMode.DEBUG
        mock_execute_child.return_value = "workflow_result"

        result = await ActionsHub._start_child_workflow_in_log_mode(
            workflow_name="TestWorkflow",
            action_name="TestWorkflow",
            node_id="TestWorkflow#1",
            result_type=str,
            args=(),
            memo={"key": "value"},
            task_queue="custom-queue",
        )

        # Verify all kwargs were passed through
        mock_execute_child.assert_called_once_with(
            "TestWorkflow",
            result_type=str,
            args=(),
            memo={"key": "value"},
            task_queue="custom-queue",
        )
        assert result == "workflow_result"

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_start_child_workflow_mocked_in_simulation(
        self,
        mock_get_simulation_response,
        mock_execute_child,
        mock_workflow_info,
        mock_get_mode,
        mock_get_log_mode,
    ):
        """Test that start_child_workflow returns mocked result from simulation."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_get_log_mode.return_value = LogMode.DEBUG
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)

        # Mock simulation response
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.MOCK, execution_response="mocked_result"
        )

        result = await ActionsHub.start_child_workflow("TestWorkflow")

        # Should return mocked result without calling execute_child_workflow
        mock_execute_child.assert_not_called()
        assert result == "mocked_result"

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_log_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    async def test_start_child_workflow_in_log_mode_with_callable(
        self,
        mock_execute_child,
        mock_get_log_mode,
    ):
        """Test _start_child_workflow_in_log_mode works with callable workflow."""
        mock_get_log_mode.return_value = LogMode.DEBUG
        mock_execute_child.return_value = "workflow_result"

        async def test_workflow():
            return "result"

        result = await ActionsHub._start_child_workflow_in_log_mode(
            workflow_name=test_workflow,
            action_name="test_workflow",
            node_id="test_workflow#1",
            result_type=str,
            args=(),
        )

        # Verify callable was passed correctly
        mock_execute_child.assert_called_once_with(
            test_workflow,
            result_type=str,
            args=(),
        )
        assert result == "workflow_result"
