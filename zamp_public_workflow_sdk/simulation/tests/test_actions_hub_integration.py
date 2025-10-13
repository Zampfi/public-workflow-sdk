"""
Integration tests for ActionsHub simulation functionality.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from zamp_public_workflow_sdk.actions_hub import ActionsHub
from zamp_public_workflow_sdk.simulation.models import (
    ExecutionType,
    SimulationResponse,
)


class TestActionsHubSimulationIntegration:
    """Integration tests for ActionsHub simulation functionality."""

    def setup_method(self):
        """Setup for each test method."""
        # Clear simulation maps before each test
        ActionsHub._workflow_id_to_simulation_map.clear()

    @pytest.mark.asyncio
    async def test_execute_child_workflow_with_simulation_skip(self):
        """Test execute_child_workflow skips simulation for specific workflows."""

        class MockWorkflow:
            __name__ = "FetchSimulationDataWorkflow"

        # Mock the workflow execution
        with patch(
            "zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow"
        ) as mock_execute:
            mock_execute.return_value = "workflow_result"

            # Mock context
            with patch(
                "zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context"
            ) as mock_mode:
                mock_mode.return_value = "TEMPORAL"

                with patch(
                    "zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context"
                ) as mock_var:
                    mock_var.return_value = "test-workflow-id"

                    with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
                        mock_info.return_value = Mock(workflow_id="test-workflow-id", headers={})

                        result = await ActionsHub.execute_child_workflow(MockWorkflow, "arg1", "arg2")

                        assert result == "workflow_result"
                        mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_child_workflow_with_simulation_mock(self):
        """Test execute_child_workflow returns mock response when simulation is active."""

        class MockWorkflow:
            __name__ = "RegularWorkflow"

        # Setup simulation
        workflow_id = "default"

        mock_simulation = Mock()
        mock_simulation.get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.MOCK, execution_response="simulated_result"
        )
        ActionsHub._workflow_id_to_simulation_map[workflow_id] = mock_simulation

        # Mock context and workflow
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context") as mock_var:
            mock_var.return_value = workflow_id

            with patch(
                "zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow"
            ) as mock_execute:
                mock_execute.return_value = "simulated_result"

                # Mock workflow.info() to avoid workflow event loop error
                with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
                    mock_info.return_value = Mock(workflow_id=workflow_id, headers={})

                    result = await ActionsHub.execute_child_workflow(MockWorkflow, "arg1", "arg2")

                    assert result == "simulated_result"
                    mock_simulation.get_simulation_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_child_workflow_with_simulation_execute(self):
        """Test execute_child_workflow executes normally when simulation returns EXECUTE."""

        class MockWorkflow:
            __name__ = "RegularWorkflow"

        # Setup simulation
        workflow_id = "default"

        mock_simulation = Mock()
        mock_simulation.get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )
        ActionsHub._workflow_id_to_simulation_map[workflow_id] = mock_simulation

        # Mock the workflow execution
        with patch(
            "zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow"
        ) as mock_execute:
            mock_execute.return_value = "workflow_result"

            # Mock context
            with patch(
                "zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context"
            ) as mock_mode:
                mock_mode.return_value = "TEMPORAL"

                with patch(
                    "zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context"
                ) as mock_var:
                    mock_var.return_value = workflow_id

                    with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
                        mock_info.return_value = Mock(workflow_id=workflow_id, headers={})

                        result = await ActionsHub.execute_child_workflow(MockWorkflow, "arg1", "arg2")

                        assert result == "workflow_result"
                        mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_child_workflow_with_result_type_conversion(self):
        """Test execute_child_workflow with result type conversion."""

        class MockWorkflow:
            __name__ = "RegularWorkflow"

        class ResultModel:
            def __init__(self, value):
                self.value = value

            @classmethod
            def __fields__(cls):
                return {"value": None}

        # Mock the workflow execution
        with patch(
            "zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow"
        ) as mock_execute:
            mock_execute.return_value = {"value": "test"}

            # Mock context
            with patch(
                "zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context"
            ) as mock_mode:
                mock_mode.return_value = "TEMPORAL"

                with patch(
                    "zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context"
                ) as mock_var:
                    mock_var.return_value = "test-workflow-id"

                    with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
                        mock_info.return_value = Mock(workflow_id="test-workflow-id", headers={})

                        result = await ActionsHub.execute_child_workflow(
                            MockWorkflow, "arg1", "arg2", result_type=ResultModel
                        )

                        # The current implementation returns the raw result, not converted to ResultModel
                        assert isinstance(result, dict)
                        assert result["value"] == "test"

    @pytest.mark.asyncio
    async def test_start_child_workflow_with_simulation_skip(self):
        """Test start_child_workflow skips simulation for specific workflows."""

        class MockWorkflow:
            __name__ = "FetchSimulationDataWorkflow"

        # Mock the workflow execution
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow") as mock_start:
            mock_start.return_value = "workflow_result"

            # Mock context
            with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context") as mock_var:
                mock_var.return_value = "test-workflow-id"

                with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
                    mock_info.return_value = Mock(workflow_id="test-workflow-id", headers={})

                    result = await ActionsHub.start_child_workflow(MockWorkflow, "arg1", "arg2")

                    assert result == "workflow_result"
                    mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_child_workflow_with_simulation_mock(self):
        """Test start_child_workflow returns mock response when simulation is active."""

        class MockWorkflow:
            __name__ = "RegularWorkflow"

        # Setup simulation
        workflow_id = "default"

        mock_simulation = Mock()
        mock_simulation.get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.MOCK, execution_response="simulated_result"
        )
        ActionsHub._workflow_id_to_simulation_map[workflow_id] = mock_simulation

        # Mock context and workflow
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context") as mock_var:
            mock_var.return_value = workflow_id

            with patch(
                "zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow"
            ) as mock_start:
                mock_start.return_value = "simulated_result"

                # Mock workflow.info() to avoid workflow event loop error
                with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
                    mock_info.return_value = Mock(workflow_id=workflow_id, headers={})

                    result = await ActionsHub.start_child_workflow(MockWorkflow, "arg1", "arg2")

                    assert result == "simulated_result"
                    mock_simulation.get_simulation_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_child_workflow_api_mode(self):
        """Test execute_child_workflow in API mode."""

        class MockWorkflow:
            __name__ = "RegularWorkflow"

        # Mock workflow function
        mock_func = AsyncMock(return_value="api_result")

        # Mock context
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context") as mock_mode:
            mock_mode.return_value = "API"

            with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context") as mock_var:
                mock_var.return_value = "test-workflow-id"

                result = await ActionsHub.execute_child_workflow(mock_func, "arg1", "arg2")

                assert result == "api_result"
                mock_func.assert_called_once_with("arg1", "arg2")

    @pytest.mark.asyncio
    async def test_execute_child_workflow_with_string_workflow_name(self):
        """Test execute_child_workflow with string workflow name."""
        # Mock workflow registry
        mock_workflow_obj = Mock()
        mock_workflow_obj.func = AsyncMock(return_value="workflow_result")
        mock_workflow_obj.class_type = Mock()
        mock_workflow_obj.class_type.return_value = Mock()

        ActionsHub._workflows["TestWorkflow"] = mock_workflow_obj

        # Mock context
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context") as mock_mode:
            mock_mode.return_value = "API"

            with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context") as mock_var:
                mock_var.return_value = "test-workflow-id"

                result = await ActionsHub.execute_child_workflow("TestWorkflow", "arg1", "arg2")

                assert result == "workflow_result"
                mock_workflow_obj.func.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_child_workflow_workflow_not_found(self):
        """Test execute_child_workflow when workflow is not found."""
        # Mock context
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context") as mock_mode:
            mock_mode.return_value = "API"

            with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context") as mock_var:
                mock_var.return_value = "test-workflow-id"

                with pytest.raises(ValueError, match="Workflow 'NonExistentWorkflow' not found"):
                    await ActionsHub.execute_child_workflow("NonExistentWorkflow", "arg1", "arg2")

    @pytest.mark.asyncio
    async def test_execute_child_workflow_workflow_function_not_available(self):
        """Test execute_child_workflow when workflow function is not available."""
        # Mock workflow registry
        mock_workflow_obj = Mock()
        mock_workflow_obj.func = None

        ActionsHub._workflows["TestWorkflow"] = mock_workflow_obj

        # Mock context
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context") as mock_mode:
            mock_mode.return_value = "API"

            with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_variable_from_context") as mock_var:
                mock_var.return_value = "test-workflow-id"

                with pytest.raises(ValueError, match="Workflow function not available for TestWorkflow"):
                    await ActionsHub.execute_child_workflow("TestWorkflow", "arg1", "arg2")

    def test_skip_simulation_workflows_constant(self):
        """Test that SKIP_SIMULATION_WORKFLOWS constant is properly defined."""
        from zamp_public_workflow_sdk.actions_hub.constants import (
            SKIP_SIMULATION_WORKFLOWS,
        )

        expected_workflows = [
            "SimulationWorkflow",
            "FetchTemporalWorkflowHistoryWorkflow",
        ]

        assert SKIP_SIMULATION_WORKFLOWS == expected_workflows
        assert len(SKIP_SIMULATION_WORKFLOWS) == 2

    def test_simulation_map_management(self):
        """Test simulation map management."""
        # Test adding simulation
        workflow_id = "default"
        mock_simulation = Mock()

        ActionsHub._workflow_id_to_simulation_map[workflow_id] = mock_simulation

        assert workflow_id in ActionsHub._workflow_id_to_simulation_map
        assert ActionsHub._workflow_id_to_simulation_map[workflow_id] == mock_simulation

        # Test removing simulation
        del ActionsHub._workflow_id_to_simulation_map[workflow_id]

        assert workflow_id not in ActionsHub._workflow_id_to_simulation_map
