"""
Tests for ActionsHub simulation methods.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.simulation.models import (
    ExecutionType,
    NodeMockConfig,
    NodePayload,
    SimulationConfig,
    SimulationResponse,
)
from zamp_public_workflow_sdk.simulation.models.mocked_result import MockedResultOutput
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

    @pytest.mark.asyncio
    async def test_get_simulation_response_action_should_skip(self):
        """Test _get_simulation_response when action should skip simulation."""

        class SimulationFetchDataWorkflow:
            pass

        result = await ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="node_1",
            action=SimulationFetchDataWorkflow,
            return_type=None,
        )

        assert result.execution_type == ExecutionType.EXECUTE
        assert result.execution_response is None

    @pytest.mark.asyncio
    async def test_get_simulation_response_no_simulation_registered(self):
        """Test _get_simulation_response when no simulation is registered."""

        class TestWorkflow:
            pass

        result = await ActionsHub._get_simulation_response(
            workflow_id="test_wf", node_id="node_1", action="test_action", return_type=None
        )

        assert result.execution_type == ExecutionType.EXECUTE
        assert result.execution_response is None

    @pytest.mark.asyncio
    async def test_get_simulation_response_with_mock_response(self):
        """Test _get_simulation_response when simulation returns MOCK."""

        class TestWorkflow:
            pass

        # Create mock simulation service
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(execution_type=ExecutionType.MOCK, execution_response={"result": "mocked"})
        mock_simulation.get_simulation_response = AsyncMock(return_value=mock_response)

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        result = await ActionsHub._get_simulation_response(
            workflow_id="test_wf", node_id="node_1", action="test_action", return_type=None
        )

        assert result.execution_type == ExecutionType.MOCK
        assert result.execution_response == {"result": "mocked"}
        mock_simulation.get_simulation_response.assert_called_once_with("node_1", action_name="test_action")

    @pytest.mark.asyncio
    async def test_get_simulation_response_with_execute_response(self):
        """Test _get_simulation_response when simulation returns EXECUTE."""

        class TestWorkflow:
            pass

        # Create mock simulation service
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(execution_type=ExecutionType.EXECUTE, execution_response=None)
        mock_simulation.get_simulation_response = AsyncMock(return_value=mock_response)

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        result = await ActionsHub._get_simulation_response(
            workflow_id="test_wf", node_id="node_1", action="test_action", return_type=None
        )

        assert result.execution_type == ExecutionType.EXECUTE
        assert result.execution_response is None

    @pytest.mark.asyncio
    async def test_get_simulation_response_with_return_type_conversion(self):
        """Test _get_simulation_response with return type conversion."""

        class TestWorkflow:
            pass

        class TestModel(BaseModel):
            value: str

        # Create mock simulation service
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(execution_type=ExecutionType.MOCK, execution_response={"value": "test"})
        mock_simulation.get_simulation_response = AsyncMock(return_value=mock_response)

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        result = await ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="node_1",
            action="test_action",
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
        assert return_type is str

    def test_get_action_return_type_with_callable_action(self):
        """Test _get_action_return_type with callable action."""

        # Register a test activity
        @ActionsHub.register_activity("Test activity with callable")
        def test_activity_callable() -> int:
            return 42

        return_type = ActionsHub._get_action_return_type(test_activity_callable)
        assert return_type is int

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
        # Should convert non-dict result to Pydantic model when return type has single field
        assert isinstance(converted, TestModel)
        assert converted.value == "plain_string"

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
            await ActionsHub.init_simulation_for_workflow(simulation_config, workflow_id="test_workflow_123")

            # Check that simulation was registered
            assert "test_workflow_123" in ActionsHub._workflow_id_to_simulation_map
            simulation = ActionsHub._workflow_id_to_simulation_map["test_workflow_123"]
            assert isinstance(simulation, WorkflowSimulationService)
            assert simulation.simulation_config == simulation_config

    @pytest.mark.asyncio
    async def test_init_simulation_for_workflow_with_explicit_workflow_id(self):
        """Test init_simulation_for_workflow with explicit workflow_id."""
        simulation_config = SimulationConfig(
            mock_config=NodeMockConfig(node_strategies=[]),
        )

        # Mock _initialize_simulation_data
        with patch.object(
            WorkflowSimulationService,
            "_initialize_simulation_data",
            new_callable=AsyncMock,
        ):
            await ActionsHub.init_simulation_for_workflow(simulation_config, workflow_id="explicit_wf")

            # Check that simulation was registered with explicit workflow id
            assert "explicit_wf" in ActionsHub._workflow_id_to_simulation_map
            simulation = ActionsHub._workflow_id_to_simulation_map["explicit_wf"]
            assert isinstance(simulation, WorkflowSimulationService)

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

    def test_get_simulation_from_workflow_id_with_parent_simulation(self):
        """Test get_simulation_from_workflow_id finds parent's simulation for child workflow."""
        mock_simulation = Mock(spec=WorkflowSimulationService)
        ActionsHub._workflow_id_to_simulation_map["parent_wf"] = mock_simulation

        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
            mock_parent = Mock()
            mock_parent.workflow_id = "parent_wf"

            # Create a proper mock info object with parent attribute
            mock_info_obj = Mock()
            mock_info_obj.parent = mock_parent
            mock_info.return_value = mock_info_obj

            result = ActionsHub.get_simulation_from_workflow_id("child_wf")

            assert result == mock_simulation
            # Verify that child workflow now has the simulation cached
            assert ActionsHub._workflow_id_to_simulation_map["child_wf"] == mock_simulation

    def test_get_simulation_from_workflow_id_parent_has_no_simulation(self):
        """Test get_simulation_from_workflow_id when parent exists but has no simulation."""
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
            mock_parent = Mock()
            mock_parent.workflow_id = "parent_wf"

            # Create a proper mock info object with parent attribute
            mock_info_obj = Mock()
            mock_info_obj.parent = mock_parent
            mock_info.return_value = mock_info_obj

            result = ActionsHub.get_simulation_from_workflow_id("child_wf")

            assert result is None

    def test_get_simulation_from_workflow_id_no_parent(self):
        """Test get_simulation_from_workflow_id when workflow has no parent."""
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
            # Create a proper mock info object with no parent
            mock_info_obj = Mock()
            mock_info_obj.parent = None
            mock_info.return_value = mock_info_obj

            result = ActionsHub.get_simulation_from_workflow_id("workflow_wf")

            assert result is None

    def test_get_simulation_from_workflow_id_workflow_info_error(self):
        """Test get_simulation_from_workflow_id when workflow.info() raises an error."""
        # Mock workflow.info() to raise an exception
        with patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info") as mock_info:
            mock_info.side_effect = Exception("Not in workflow event loop")

            result = ActionsHub.get_simulation_from_workflow_id("workflow_wf")

            assert result is None

    @pytest.mark.asyncio
    async def test_execute_activity_simulation_integration(self):
        """Test that execute_activity integrates with simulation response."""
        # This tests the integration between execute_activity and _get_simulation_response
        # through mocking

        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(execution_type=ExecutionType.MOCK, execution_response="mocked_result")
        mock_simulation.get_simulation_response = AsyncMock(return_value=mock_response)
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        # Test that _get_simulation_response returns the mocked result
        result = await ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="test_node",
            action="test_activity",
            return_type=None,
        )

        assert result.execution_type == ExecutionType.MOCK
        assert result.execution_response == "mocked_result"

    @pytest.mark.asyncio
    async def test_child_workflow_simulation_integration(self):
        """Test that child workflow execution integrates with simulation response."""
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(execution_type=ExecutionType.MOCK, execution_response="mocked_workflow")
        mock_simulation.get_simulation_response = AsyncMock(return_value=mock_response)
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        # Test that _get_simulation_response returns the mocked result
        result = await ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="test_node",
            action="TestWorkflow",
            return_type=None,
        )

        assert result.execution_type == ExecutionType.MOCK
        assert result.execution_response == "mocked_workflow"

    @pytest.mark.asyncio
    async def test_start_child_workflow_simulation_integration(self):
        """Test that start_child_workflow integrates with simulation response."""
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(execution_type=ExecutionType.MOCK, execution_response="mocked_start")
        mock_simulation.get_simulation_response = AsyncMock(return_value=mock_response)
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        # Test that _get_simulation_response returns the mocked result
        result = await ActionsHub._get_simulation_response(
            workflow_id="test_wf",
            node_id="test_node",
            action="TestWorkflow",
            return_type=None,
        )

        assert result.execution_type == ExecutionType.MOCK
        assert result.execution_response == "mocked_start"

    @pytest.mark.asyncio
    async def test_get_simulation_response_with_action_return_type_inference(self):
        """Test _get_simulation_response infers return type from action."""

        # Register a test activity
        @ActionsHub.register_activity("Test activity for type inference")
        def test_activity_type() -> str:
            return "test"

        # Create mock simulation service
        mock_simulation = Mock(spec=WorkflowSimulationService)
        mock_response = SimulationResponse(execution_type=ExecutionType.MOCK, execution_response={"value": "test"})
        mock_simulation.get_simulation_response = AsyncMock(return_value=mock_response)

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = mock_simulation

        # Call with action but no return_type - should call _get_action_return_type
        with patch.object(ActionsHub, "_get_action_return_type", return_value=str) as mock_get_return_type:
            await ActionsHub._get_simulation_response(
                workflow_id="test_wf",
                node_id="node_1",
                action=test_activity_type,
                return_type=None,
            )

            # Should have called _get_action_return_type
            mock_get_return_type.assert_called_once_with(test_activity_type)

    @pytest.mark.asyncio
    async def test_get_simulation_response_with_encoded_payload_decoding_success(self):
        """Test _get_simulation_response with encoded payload that needs decoding."""

        # Create real simulation service with encoded payload
        simulation = WorkflowSimulationService(None)
        encoded_output = {"metadata": {"encoding": "json/plain"}, "data": "encoded_data_here"}
        simulation.node_id_to_payload_map = {
            "node_1": NodePayload(node_id="node_1", input_payload=None, output_payload=encoded_output)
        }

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = simulation

        # Mock ActionsHub.execute_activity for return_mocked_result
        with patch(
            "zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub.execute_activity", new_callable=AsyncMock
        ) as mock_execute:
            decoded_data = {"result": "decoded_value"}
            mock_result = MockedResultOutput(root=decoded_data)
            mock_execute.return_value = mock_result

            result = await ActionsHub._get_simulation_response(
                workflow_id="test_wf",
                node_id="node_1",
                action="test_action",
                return_type=None,
            )

            assert result.execution_type == ExecutionType.MOCK
            assert result.execution_response == mock_result
            # Verify return_mocked_result activity was called
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][0] == "return_mocked_result"

    @pytest.mark.asyncio
    async def test_get_simulation_response_with_encoded_payload_decoding_failure(self):
        """Test _get_simulation_response when decoding fails."""

        # Create real simulation service with encoded payload
        simulation = WorkflowSimulationService(None)
        encoded_output = {"metadata": {"encoding": "json/plain"}, "data": "encoded_data_here"}
        simulation.node_id_to_payload_map = {
            "node_1": NodePayload(node_id="node_1", input_payload=None, output_payload=encoded_output)
        }

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = simulation

        # Mock ActionsHub.execute_activity to raise an exception
        with patch(
            "zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub.execute_activity", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = Exception("Decoding failed")

            with pytest.raises(Exception, match="Decoding failed"):
                await ActionsHub._get_simulation_response(
                    workflow_id="test_wf",
                    node_id="node_1",
                    action="test_action",
                    return_type=None,
                )

    @pytest.mark.asyncio
    async def test_get_simulation_response_with_unencoded_payload_no_decoding(self):
        """Test _get_simulation_response with payload that doesn't need decoding (CustomOutputStrategy)."""

        # Create real simulation service with raw payload (no encoding metadata)
        simulation = WorkflowSimulationService(None)
        raw_payload = {"result": "raw_value"}
        simulation.node_id_to_payload_map = {
            "node_1": NodePayload(node_id="node_1", input_payload=None, output_payload=raw_payload)
        }

        # Register the simulation
        ActionsHub._workflow_id_to_simulation_map["test_wf"] = simulation

        # Mock ActionsHub.execute_activity - return_mocked_result should be called but no decoding should happen
        with patch(
            "zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub.execute_activity", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MockedResultOutput(root=raw_payload)
            mock_execute.return_value = mock_result
            result = await ActionsHub._get_simulation_response(
                workflow_id="test_wf",
                node_id="node_1",
                action="test_action",
                return_type=None,
            )

            assert result.execution_type == ExecutionType.MOCK
            assert result.execution_response == mock_result
            # Verify return_mocked_result activity was called (it handles both encoded and raw)
            mock_execute.assert_called_once()
