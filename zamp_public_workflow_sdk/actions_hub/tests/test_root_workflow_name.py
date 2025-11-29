from unittest.mock import Mock, patch

import pytest

from zamp_public_workflow_sdk.actions_hub.action_hub_core import ActionsHub
from zamp_public_workflow_sdk.actions_hub.constants import ExecutionMode


class TestGetRootWorkflowName:
    """Test cases for _get_root_workflow_name method."""

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.payload_converter")
    def test_inherits_from_headers(self, mock_payload_converter, mock_workflow_info):
        """Test that root_workflow_name is inherited from headers (highest priority)."""
        mock_payload = Mock()
        mock_headers = {"root_workflow_name": mock_payload}
        mock_workflow_info.return_value = Mock(headers=mock_headers)
        mock_payload_converter.return_value.from_payload.return_value = "inherited-root-workflow"

        result = ActionsHub._get_root_workflow_name("should-be-ignored")

        assert result == "inherited-root-workflow"
        mock_payload_converter.return_value.from_payload.assert_called_once_with(mock_payload, str)

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_uses_provided_name_when_no_headers(self, mock_workflow_info):
        """Test that provided name is used when no headers present."""
        mock_workflow_info.return_value = Mock(headers=None)

        result = ActionsHub._get_root_workflow_name("custom-workflow-name")

        assert result == "custom-workflow-name"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_uses_provided_name_when_header_key_missing(self, mock_workflow_info):
        """Test that provided name is used when header key is missing."""
        mock_workflow_info.return_value = Mock(headers={"other_key": "value"})

        result = ActionsHub._get_root_workflow_name("custom-workflow-name")

        assert result == "custom-workflow-name"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_returns_workflow_type_when_no_headers_and_no_provided_name(self, mock_workflow_info):
        """Test that workflow_type is returned when no headers and no provided name."""
        mock_workflow_info.return_value = Mock(headers=None, workflow_type="CurrentWorkflow")

        result = ActionsHub._get_root_workflow_name(None)

        assert result == "CurrentWorkflow"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    def test_returns_workflow_type_when_empty_provided_name(self, mock_workflow_info):
        """Test that workflow_type is returned when provided name is empty string."""
        mock_workflow_info.return_value = Mock(headers=None, workflow_type="CurrentWorkflow")

        result = ActionsHub._get_root_workflow_name("")

        assert result == "CurrentWorkflow"

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.payload_converter")
    def test_header_takes_priority_over_provided_name(self, mock_payload_converter, mock_workflow_info):
        """Test that header value takes priority over provided name (for chain preservation)."""
        mock_payload = Mock()
        mock_headers = {"root_workflow_name": mock_payload}
        mock_workflow_info.return_value = Mock(headers=mock_headers)
        mock_payload_converter.return_value.from_payload.return_value = "header-value"

        result = ActionsHub._get_root_workflow_name("provided-but-ignored")

        assert result == "header-value"


class TestUpsertRootWorkflowSearchAttribute:
    """Test cases for _upsert_root_workflow_search_attribute method."""

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    def test_upsert_called_with_correct_format(self, mock_upsert):
        """Test that upsert_search_attributes is called with correct format."""
        ActionsHub._upsert_root_workflow_search_attribute("TestWorkflow")

        mock_upsert.assert_called_once_with({"RootWorkflowName": ["TestWorkflow"]})

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    def test_upsert_not_called_with_empty_name(self, mock_upsert):
        """Test that upsert is not called when root_workflow_name is empty."""
        ActionsHub._upsert_root_workflow_search_attribute("")

        mock_upsert.assert_not_called()

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    def test_upsert_not_called_with_none(self, mock_upsert):
        """Test that upsert is not called when root_workflow_name is None."""
        ActionsHub._upsert_root_workflow_search_attribute(None)

        mock_upsert.assert_not_called()

    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    def test_upsert_with_complex_name(self, mock_upsert):
        """Test upserting with complex workflow name."""
        ActionsHub._upsert_root_workflow_search_attribute("My_Complex_Workflow_123")

        mock_upsert.assert_called_once_with({"RootWorkflowName": ["My_Complex_Workflow_123"]})


class TestExecuteChildWorkflowRootWorkflowName:
    """Integration tests for execute_child_workflow with RootWorkflowName."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()
        ActionsHub._activities.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_execute_child_workflow_uses_workflow_type_as_fallback(
        self, mock_get_simulation_response, mock_workflow_info, mock_get_mode, mock_execute_child, mock_upsert
    ):
        """Test that workflow_type is used as fallback when no root_workflow_name is set."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(
            workflow_id="test-workflow", headers=None, workflow_type="ParentWorkflow"
        )
        mock_execute_child.return_value = "workflow_result"
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        await ActionsHub.execute_child_workflow("ChildWorkflow")

        # Verify upsert was called with workflow_type as fallback
        mock_upsert.assert_called_once_with({"RootWorkflowName": ["ParentWorkflow"]})

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_execute_child_workflow_uses_provided_root_workflow_name(
        self, mock_get_simulation_response, mock_workflow_info, mock_get_mode, mock_execute_child, mock_upsert
    ):
        """Test that execute_child_workflow uses provided root_workflow_name (CustomerCodeWorkflow case)."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_execute_child.return_value = "workflow_result"
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        # CustomerCodeWorkflow case - pass custom workflow name
        await ActionsHub.execute_child_workflow("ChildWorkflow", root_workflow_name="custom-order-123-workflow")

        # Verify upsert was called with the provided custom name
        mock_upsert.assert_called_once_with({"RootWorkflowName": ["custom-order-123-workflow"]})

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.payload_converter")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_execute_child_workflow_inherits_from_headers(
        self,
        mock_get_simulation_response,
        mock_payload_converter,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_child,
        mock_upsert,
    ):
        """Test that execute_child_workflow inherits root_workflow_name from headers."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_payload = Mock()
        mock_headers = {"root_workflow_name": mock_payload}
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=mock_headers)
        mock_payload_converter.return_value.from_payload.return_value = "inherited-root-name"
        mock_execute_child.return_value = "workflow_result"
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        # Even if we pass a different name, header takes priority
        await ActionsHub.execute_child_workflow("ChildWorkflow", root_workflow_name="this-should-be-ignored")

        # Verify upsert was called with the inherited name from headers
        mock_upsert.assert_called_once_with({"RootWorkflowName": ["inherited-root-name"]})

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    async def test_execute_child_workflow_api_mode_no_upsert(self, mock_get_mode, mock_upsert):
        """Test that API mode does not call upsert_search_attributes."""
        mock_get_mode.return_value = ExecutionMode.API

        async def mock_workflow_func(*args, **kwargs):
            return "workflow_result"

        class MockWorkflowClass:
            pass

        from zamp_public_workflow_sdk.actions_hub.models.workflow_models import Workflow

        ActionsHub._workflows["TestWorkflow"] = Workflow(
            name="TestWorkflow",
            description="Test workflow",
            labels=[],
            class_type=MockWorkflowClass,
            func=mock_workflow_func,
        )

        await ActionsHub.execute_child_workflow("TestWorkflow", root_workflow_name="custom-name")

        mock_upsert.assert_not_called()


class TestStartChildWorkflowRootWorkflowName:
    """Integration tests for start_child_workflow with RootWorkflowName."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()
        ActionsHub._activities.clear()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_start_child_workflow_uses_workflow_type_as_fallback(
        self, mock_get_simulation_response, mock_workflow_info, mock_get_mode, mock_start_child, mock_upsert
    ):
        """Test that workflow_type is used as fallback when no root_workflow_name is set."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(
            workflow_id="test-workflow", headers=None, workflow_type="ParentWorkflow"
        )
        mock_start_child.return_value = Mock()
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        await ActionsHub.start_child_workflow("ChildWorkflow")

        mock_upsert.assert_called_once_with({"RootWorkflowName": ["ParentWorkflow"]})

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_start_child_workflow_uses_provided_root_workflow_name(
        self, mock_get_simulation_response, mock_workflow_info, mock_get_mode, mock_start_child, mock_upsert
    ):
        """Test that start_child_workflow uses provided root_workflow_name."""
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="test-workflow", headers=None)
        mock_start_child.return_value = Mock()
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        await ActionsHub.start_child_workflow("ChildWorkflow", root_workflow_name="custom-order-456-workflow")

        mock_upsert.assert_called_once_with({"RootWorkflowName": ["custom-order-456-workflow"]})

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.start_child_workflow")
    async def test_start_child_workflow_skip_node_id_gen_no_upsert(self, mock_start_child, mock_upsert):
        """Test that skip_node_id_gen=True does not call upsert_search_attributes."""
        mock_start_child.return_value = Mock()

        await ActionsHub.start_child_workflow("ChildWorkflow", skip_node_id_gen=True)

        mock_upsert.assert_not_called()


class TestCustomerCodeWorkflowScenario:
    """Test the CustomerCodeWorkflow use case specifically."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_customer_code_workflow_passes_custom_workflow_name(
        self, mock_get_simulation_response, mock_workflow_info, mock_get_mode, mock_execute_child, mock_upsert
    ):
        """
        Test CustomerCodeWorkflow scenario where customWorkflowName is passed.

        CustomerCodeWorkflow has a customWorkflowName attribute that should be
        used as the RootWorkflowName for all its child workflows.
        """
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="customer-code-workflow-123", headers=None)
        mock_execute_child.return_value = "workflow_result"
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        # Simulate CustomerCodeWorkflow calling child with its customWorkflowName
        custom_workflow_name = "order-processor-customer-abc-12345"

        await ActionsHub.execute_child_workflow(
            "ProcessOrderWorkflow", {"order_id": "12345"}, root_workflow_name=custom_workflow_name
        )

        # Verify the custom name was used
        mock_upsert.assert_called_once_with({"RootWorkflowName": [custom_workflow_name]})


class TestChainedWorkflowScenario:
    """Test the chained workflow scenario where root_workflow_name propagates through chain."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        ActionsHub.clear_node_id_tracker()

    def teardown_method(self):
        """Clean up after each test method."""
        ActionsHub.clear_node_id_tracker()

    @pytest.mark.asyncio
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.upsert_search_attributes")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.execute_child_workflow")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.get_execution_mode_from_context")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.info")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.workflow.payload_converter")
    @patch("zamp_public_workflow_sdk.actions_hub.action_hub_core.ActionsHub._get_simulation_response")
    async def test_nested_workflow_inherits_root_name_from_chain(
        self,
        mock_get_simulation_response,
        mock_payload_converter,
        mock_workflow_info,
        mock_get_mode,
        mock_execute_child,
        mock_upsert,
    ):
        """
        Test that nested workflows inherit root_workflow_name from the chain.

        Scenario:
        CustomerCodeWorkflow (sets "order-123")
          └── UniversalWorkflow (inherits "order-123" from headers)
                └── CustomerCodeWorkflow (inherits "order-123" from headers, NOT its own customWorkflowName)
        """
        from zamp_public_workflow_sdk.simulation.models import ExecutionType, SimulationResponse

        # Simulate being in a nested workflow that has inherited root_workflow_name in headers
        mock_payload = Mock()
        mock_headers = {"root_workflow_name": mock_payload}
        mock_get_mode.return_value = ExecutionMode.TEMPORAL
        mock_workflow_info.return_value = Mock(workflow_id="nested-workflow", headers=mock_headers)
        mock_payload_converter.return_value.from_payload.return_value = "original-root-from-chain"
        mock_execute_child.return_value = "workflow_result"
        mock_get_simulation_response.return_value = SimulationResponse(
            execution_type=ExecutionType.EXECUTE, execution_response=None
        )

        # Even if this nested CustomerCodeWorkflow has its own customWorkflowName,
        # it should use the inherited value from the chain
        await ActionsHub.execute_child_workflow(
            "AnotherChildWorkflow", root_workflow_name="my-own-custom-name-should-be-ignored"
        )

        # Verify the inherited name was used (not the provided one)
        mock_upsert.assert_called_once_with({"RootWorkflowName": ["original-root-from-chain"]})
