"""
Tests for ActionsHub simulation methods.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pydantic import BaseModel

from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.models.core_models import ActionFilter
from zamp_public_workflow_sdk.simulation.models import (
    SimulationConfig,
    SimulationResponse,
    ExecutionType,
    NodeMockConfig,
)
from zamp_public_workflow_sdk.simulation.workflow_simulation_service import (
    WorkflowSimulationService,
)


class TestActionsHubSimulation:
    """Test ActionsHub simulation methods."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear simulation map before each test
        ActionsHub._workflow_id_to_simulation_map.clear()
        ActionsHub._activities.clear()
        ActionsHub._workflows.clear()

    def teardown_method(self):
        """Clean up after each test."""
        ActionsHub._workflow_id_to_simulation_map.clear()
        ActionsHub._activities.clear()
        ActionsHub._workflows.clear()

    def test_should_skip_simulation_with_callable_in_skip_list(self):
        """Test _should_skip_simulation with callable in skip list."""

        class SimulationWorkflow:
            pass

        result = ActionsHub._should_skip_simulation(SimulationWorkflow)
        assert result is True

    def test_should_skip_simulation_with_callable_not_in_skip_list(self):
        """Test _should_skip_simulation with callable not in skip list."""

        class RegularWorkflow:
            pass

        result = ActionsHub._should_skip_simulation(RegularWorkflow)
        assert result is False

    def test_should_skip_simulation_with_string_in_skip_list(self):
        """Test _should_skip_simulation with string in skip list."""
        result = ActionsHub._should_skip_simulation("SimulationWorkflow")
        assert result is True

    def test_should_skip_simulation_with_string_not_in_skip_list(self):
        """Test _should_skip_simulation with string not in skip list."""
        result = ActionsHub._should_skip_simulation("RegularWorkflow")
        assert result is False

    def test_should_skip_simulation_with_fetch_temporal_workflow(self):
        """Test _should_skip_simulation with FetchTemporalWorkflowHistoryWorkflow."""

        class FetchTemporalWorkflowHistoryWorkflow:
            pass

        result = ActionsHub._should_skip_simulation(
            FetchTemporalWorkflowHistoryWorkflow
        )
        assert result is True

    def test_get_simulation_response_action_should_skip(self):
        """Test _get_simulation_response when action should skip simulation."""

        class SimulationWorkflow:
            pass

        result = ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="node_1",
            action=SimulationWorkflow,
            return_type=None,
        )

        assert result.execution_type == ExecutionType.EXECUTE
        assert result.execution_response is None

    def test_get_simulation_response_no_simulation_registered(self):
        """Test _get_simulation_response when no simulation is registered."""
        result = ActionsHub._get_simulation_response(
            workflow_id="test_wf", node_id="node_1", action=None, return_type=None
        )

        assert result.execution_type == ExecutionType.EXECUTE
        assert result.execution_response is None

    def test_get_simulation_response_with_mock_response(self):
        """Test _get_simulation_response when simulation returns MOCK."""
        # Create mock simulation service
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(
            execution_type=ExecutionType.MOCK, execution_response={"result": "mocked"}
        )
        mock_simulation.get_simulation_response.return_value = mock_response

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        result = ActionsHub._get_simulation_response(
            workflow_id="test_wf", node_id="node_1", action=None, return_type=None
        )

        assert result.execution_type == ExecutionType.MOCK
        assert result.execution_response == {"result": "mocked"}
        mock_simulation.get_simulation_response.assert_called_once_with("node_1")

    def test_get_simulation_response_with_execute_response(self):
        """Test _get_simulation_response when simulation returns EXECUTE."""
        # Create mock simulation service
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )
        mock_simulation.get_simulation_response.return_value = mock_response

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        result = ActionsHub._get_simulation_response(
            workflow_id="test_wf", node_id="node_1", action=None, return_type=None
        )

        assert result.execution_type == ExecutionType.EXECUTE
        assert result.execution_response is None

    def test_get_simulation_response_with_return_type_conversion(self):
        """Test _get_simulation_response with return type conversion."""

        class TestModel(BaseModel):
            value: str

        # Create mock simulation service
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(
            execution_type=ExecutionType.MOCK, execution_response={"value": "test"}
        )
        mock_simulation.get_simulation_response.return_value = mock_response

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        result = ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="node_1",
            action=None,
            return_type=TestModel,
        )

        assert result.execution_type == ExecutionType.MOCK
        assert isinstance(result.execution_response, TestModel)
        assert result.execution_response.value == "test"

    def test_get_action_return_type_with_string_action(self):
        """Test _get_action_return_type with string action name."""

        # Register a test activity
        @ActionsHub.register_activity("Test activity with return type")
        def test_activity_return() -> str:
            return "test"

        return_type = ActionsHub._get_action_return_type("test_activity_return")
        assert return_type == str

    def test_get_action_return_type_with_callable_action(self):
        """Test _get_action_return_type with callable action."""

        # Register a test activity
        @ActionsHub.register_activity("Test activity with callable")
        def test_activity_callable() -> int:
            return 42

        return_type = ActionsHub._get_action_return_type(test_activity_callable)
        assert return_type == int

    def test_get_action_return_type_action_not_found(self):
        """Test _get_action_return_type when action is not found."""
        return_type = ActionsHub._get_action_return_type("non_existent_action")
        assert return_type is None

    def test_convert_result_to_model_no_return_type(self):
        """Test _convert_result_to_model with no return type."""
        result = {"key": "value"}
        converted = ActionsHub._convert_result_to_model(result, None)
        assert converted == result

    def test_convert_result_to_model_result_is_none(self):
        """Test _convert_result_to_model when result is None."""

        class TestModel(BaseModel):
            value: str

        converted = ActionsHub._convert_result_to_model(None, TestModel)
        assert converted is None

    def test_convert_result_to_model_with_pydantic_model(self):
        """Test _convert_result_to_model with Pydantic model."""

        class TestModel(BaseModel):
            name: str
            value: int

        result = {"name": "test", "value": 123}
        converted = ActionsHub._convert_result_to_model(result, TestModel)

        assert isinstance(converted, TestModel)
        assert converted.name == "test"
        assert converted.value == 123

    def test_convert_result_to_model_with_non_dict_result(self):
        """Test _convert_result_to_model with non-dict result."""

        class TestModel(BaseModel):
            value: str

        result = "plain_string"
        converted = ActionsHub._convert_result_to_model(result, TestModel)
        # Should return original result unchanged
        assert converted == result

    def test_convert_result_to_model_validation_error(self):
        """Test _convert_result_to_model when validation fails."""

        class TestModel(BaseModel):
            required_field: str

        result = {"wrong_field": "value"}
        converted = ActionsHub._convert_result_to_model(result, TestModel)
        # Should return original result on validation error
        assert converted == result

    def test_convert_result_to_model_without_model_validate(self):
        """Test _convert_result_to_model with return type that doesn't have model_validate."""
        result = {"key": "value"}
        converted = ActionsHub._convert_result_to_model(result, str)
        # Should return original result unchanged
        assert converted == result

    @pytest.mark.asyncio
    async def test_init_simulation_for_workflow_with_workflow_id(self):
        """Test init_simulation_for_workflow with provided workflow_id."""
        simulation_config = SimulationConfig(
            mock_config=NodeMockConfig(node_strategies=[]),
        )

        # Mock the _initialize_simulation_data method
        with patch.object(
            WorkflowSimulationService,
            "_initialize_simulation_data",
            new_callable=AsyncMock,
        ):
            await ActionsHub.init_simulation_for_workflow(
                simulation_config, workflow_id="test_workflow_123"
            )

            # Check that simulation was registered
            assert "test_workflow_123" in ActionsHub._workflow_id_to_simulation_map
            simulation = ActionsHub._workflow_id_to_simulation_map["test_workflow_123"]
            assert isinstance(simulation, WorkflowSimulationService)
            assert simulation.simulation_config == simulation_config

    @pytest.mark.asyncio
    async def test_init_simulation_for_workflow_without_workflow_id(self):
        """Test init_simulation_for_workflow without workflow_id (uses current)."""
        simulation_config = SimulationConfig(
            mock_config=NodeMockConfig(node_strategies=[]),
        )

        # Mock _get_current_workflow_id and _initialize_simulation_data
        with patch.object(
            ActionsHub, "_get_current_workflow_id", return_value="current_wf"
        ):
            with patch.object(
                WorkflowSimulationService,
                "_initialize_simulation_data",
                new_callable=AsyncMock,
            ):
                await ActionsHub.init_simulation_for_workflow(simulation_config)

                # Check that simulation was registered with current workflow id
                assert "current_wf" in ActionsHub._workflow_id_to_simulation_map
                simulation = ActionsHub._workflow_id_to_simulation_map["current_wf"]
                assert isinstance(simulation, WorkflowSimulationService)

    @pytest.mark.asyncio
    async def test_init_simulation_for_workflow_with_none_workflow_id(self):
        """Test init_simulation_for_workflow when _get_current_workflow_id returns None."""
        simulation_config = SimulationConfig(
            mock_config=NodeMockConfig(node_strategies=[]),
        )

        # Mock _get_current_workflow_id to return None
        with patch.object(
            ActionsHub, "_get_current_workflow_id", return_value=None
        ):
            await ActionsHub.init_simulation_for_workflow(simulation_config)

            # Check that no simulation was registered (workflow_id was None)
            assert len(ActionsHub._workflow_id_to_simulation_map) == 0

    def test_get_simulation_from_workflow_id_exists(self):
        """Test get_simulation_from_workflow_id when simulation exists."""
        mock_simulation = Mock(spec=WorkflowSimulationService)
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        result = ActionsHub.get_simulation_from_workflow_id("test_wf")
        assert result == mock_simulation

    def test_get_simulation_from_workflow_id_not_exists(self):
        """Test get_simulation_from_workflow_id when simulation doesn't exist."""
        result = ActionsHub.get_simulation_from_workflow_id("non_existent_wf")
        assert result is None

    def test_execute_activity_simulation_integration(self):
        """Test that execute_activity integrates with simulation response."""
        # This tests the integration between execute_activity and _get_simulation_response
        # through mocking

        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(
            execution_type=ExecutionType.MOCK, execution_response="mocked_result"
        )
        mock_simulation.get_simulation_response.return_value = mock_response
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        # Test that _get_simulation_response returns the mocked result
        result = ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="test_node",
            action="test_activity",
            return_type=None
        )

        assert result.execution_type == ExecutionType.MOCK
        assert result.execution_response == "mocked_result"

    def test_child_workflow_simulation_integration(self):
        """Test that child workflow execution integrates with simulation response."""
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(
            execution_type=ExecutionType.MOCK, execution_response="mocked_workflow"
        )
        mock_simulation.get_simulation_response.return_value = mock_response
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        # Test that _get_simulation_response returns the mocked result
        result = ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="test_node",
            action="TestWorkflow",
            return_type=None
        )

        assert result.execution_type == ExecutionType.MOCK
        assert result.execution_response == "mocked_workflow"

    def test_start_child_workflow_simulation_integration(self):
        """Test that start_child_workflow integrates with simulation response."""
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(
            execution_type=ExecutionType.MOCK, execution_response="mocked_start"
        )
        mock_simulation.get_simulation_response.return_value = mock_response
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        # Test that _get_simulation_response returns the mocked result
        result = ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="test_node",
            action="TestWorkflow",
            return_type=None
        )

        assert result.execution_type == ExecutionType.MOCK
        assert result.execution_response == "mocked_start"

    def test_get_simulation_response_with_action_return_type_inference(self):
        """Test _get_simulation_response infers return type from action."""

        # Register a test activity
        @ActionsHub.register_activity("Test activity for type inference")
        def test_activity_type() -> str:
            return "test"

        # Create mock simulation service
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(
            execution_type=ExecutionType.MOCK, execution_response={"value": "test"}
        )
        mock_simulation.get_simulation_response.return_value = mock_response

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        # Call with action but no return_type - should call _get_action_return_type
        with patch.object(
            ActionsHub, "_get_action_return_type", return_value=str
        ) as mock_get_return_type:
            result = ActionsHub._get_simulation_response(
                workflow_id="test_wf",
                node_id="node_1",
                action=test_activity_type,
                return_type=None,
            )

            # Should have called _get_action_return_type
            mock_get_return_type.assert_called_once_with(test_activity_type)
