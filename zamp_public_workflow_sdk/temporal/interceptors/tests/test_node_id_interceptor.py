"""
Unit and integration tests for NodeIdInterceptor.

This module contains comprehensive tests for the NodeIdInterceptor, including:
- Unit tests for individual interceptor classes
- Integration tests for complete node_id flow
- Error handling and edge case testing
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from temporalio import workflow
from temporalio.worker import (
    StartActivityInput,
    StartChildWorkflowInput,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
    WorkflowOutboundInterceptor,
)

from zamp_public_workflow_sdk.temporal.interceptors.node_id_interceptor import (
    NODE_ID_HEADER_KEY,
    NodeIdInterceptor,
    NodeIdWorkflowOutboundInterceptor,
)


# Test fixtures
@pytest.fixture
def mock_next_outbound():
    """Create a mock for the next workflow outbound interceptor."""
    next_interceptor = MagicMock(spec=WorkflowOutboundInterceptor)
    next_interceptor.start_activity = MagicMock()
    next_interceptor.start_child_workflow = AsyncMock()
    return next_interceptor


@pytest.fixture
def mock_payload_converter():
    """Mock the payload converter."""
    converter = MagicMock()
    converter.to_payload.side_effect = lambda x: f"payload:{x}"
    converter.from_payload.side_effect = lambda p, _: p.replace("payload:", "")
    return converter


@pytest.fixture
def sample_node_id():
    """Sample node_id for testing."""
    return "test_action#instance_123"


@pytest.fixture
def node_id_dict(sample_node_id):
    """Sample node_id dict format."""
    return {"__temporal_node_id": sample_node_id}


# Tests for NodeIdWorkflowOutboundInterceptor
class TestNodeIdWorkflowOutboundInterceptor:
    def test_init(self, mock_next_outbound):
        """Test interceptor initialization."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        assert interceptor.next == mock_next_outbound

    def test_extract_node_id_from_args_with_node_id(self, mock_next_outbound, node_id_dict, sample_node_id):
        """Test extracting node_id from args when present."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        args = ("arg1", node_id_dict, "arg3")
        result = interceptor._extract_node_id_from_args(args)

        assert result == sample_node_id

    def test_extract_node_id_from_args_without_node_id(self, mock_next_outbound):
        """Test extracting node_id from args when not present."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        args = ("arg1", "arg2", {"other_key": "value"})
        result = interceptor._extract_node_id_from_args(args)

        assert result is None

    def test_extract_node_id_from_args_empty(self, mock_next_outbound):
        """Test extracting node_id from empty args."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        args = ()
        result = interceptor._extract_node_id_from_args(args)

        assert result is None

    def test_extract_node_id_from_args_multiple_keys_dict(self, mock_next_outbound):
        """Test that dict with multiple keys is not considered node_id."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        args = ({"__temporal_node_id": "test", "other_key": "value"},)
        result = interceptor._extract_node_id_from_args(args)

        assert result is None

    def test_add_node_id_to_activity_headers(self, mock_next_outbound, mock_payload_converter, sample_node_id):
        """Test adding node_id to activity headers."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            input_obj = MagicMock()
            input_obj.headers = {}

            interceptor._add_node_id_to_activity_headers(input_obj, sample_node_id)

            assert NODE_ID_HEADER_KEY in input_obj.headers
            assert input_obj.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"

    def test_add_node_id_to_activity_headers_no_node_id(self, mock_next_outbound):
        """Test adding node_id to headers when node_id is None."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        input_obj = MagicMock()
        input_obj.headers = {}

        interceptor._add_node_id_to_activity_headers(input_obj, None)

        assert NODE_ID_HEADER_KEY not in input_obj.headers

    def test_add_node_id_to_activity_headers_for_child_workflow(
        self, mock_next_outbound, mock_payload_converter, sample_node_id
    ):
        """Test adding node_id to child workflow headers."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            input_obj = MagicMock(spec=StartChildWorkflowInput)
            input_obj.headers = {}

            interceptor._add_node_id_to_activity_headers(input_obj, sample_node_id)

            assert NODE_ID_HEADER_KEY in input_obj.headers
            assert input_obj.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"

    def test_add_node_id_to_activity_headers_no_headers_attr(
        self, mock_next_outbound, mock_payload_converter, sample_node_id
    ):
        """Test adding node_id to headers when headers attribute doesn't exist."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            input_obj = MagicMock(spec=StartChildWorkflowInput)
            delattr(input_obj, "headers")

            interceptor._add_node_id_to_activity_headers(input_obj, sample_node_id)

            assert hasattr(input_obj, "headers")
            assert NODE_ID_HEADER_KEY in input_obj.headers
            assert input_obj.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"

    def test_add_node_id_to_activity_headers_none_headers(
        self, mock_next_outbound, mock_payload_converter, sample_node_id
    ):
        """Test adding node_id to headers when headers is None."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            input_obj = MagicMock(spec=StartChildWorkflowInput)
            input_obj.headers = None

            interceptor._add_node_id_to_activity_headers(input_obj, sample_node_id)

            assert input_obj.headers is not None
            assert NODE_ID_HEADER_KEY in input_obj.headers
            assert input_obj.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"

    def test_filter_node_id_from_args(self, mock_next_outbound, node_id_dict):
        """Test filtering node_id dict from args."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        args = ("arg1", node_id_dict, "arg3", {"other": "dict"})
        result = interceptor._filter_node_id_from_args(args)

        expected = ("arg1", "arg3", {"other": "dict"})
        assert result == expected

    def test_filter_node_id_from_args_no_node_id(self, mock_next_outbound):
        """Test filtering args when no node_id dict is present."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        args = ("arg1", "arg2", {"other": "dict"})
        result = interceptor._filter_node_id_from_args(args)

        assert result == args

    def test_filter_node_id_from_args_empty(self, mock_next_outbound):
        """Test filtering empty args."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        args = ()
        result = interceptor._filter_node_id_from_args(args)

        assert result == args

    def test_filter_node_id_from_args_multiple_node_id_dicts(self, mock_next_outbound):
        """Test filtering args with multiple node_id dicts."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        node_id_dict1 = {"__temporal_node_id": "node1"}
        node_id_dict2 = {"__temporal_node_id": "node2"}
        args = ("arg1", node_id_dict1, "arg2", node_id_dict2, "arg3")

        result = interceptor._filter_node_id_from_args(args)

        expected = ("arg1", "arg2", "arg3")
        assert result == expected

    def test_start_activity_with_node_id(
        self, mock_next_outbound, mock_payload_converter, node_id_dict, sample_node_id
    ):
        """Test start_activity with node_id in args."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            input_obj = MagicMock(spec=StartActivityInput)
            input_obj.headers = {}
            input_obj.args = ("arg1", node_id_dict, "arg3")

            interceptor.start_activity(input_obj)

            # Verify node_id was added to headers
            assert NODE_ID_HEADER_KEY in input_obj.headers
            assert input_obj.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"

            # Verify node_id was removed from args
            assert input_obj.args == ("arg1", "arg3")

            # Verify next interceptor was called
            mock_next_outbound.start_activity.assert_called_once_with(input_obj)

    def test_start_activity_without_node_id(self, mock_next_outbound):
        """Test start_activity without node_id in args."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        input_obj = MagicMock(spec=StartActivityInput)
        input_obj.headers = {}
        original_args = ("arg1", "arg2", "arg3")
        input_obj.args = original_args

        interceptor.start_activity(input_obj)

        # Verify no headers were added
        assert NODE_ID_HEADER_KEY not in input_obj.headers

        # Verify args were not modified
        assert input_obj.args == original_args

        # Verify next interceptor was called
        mock_next_outbound.start_activity.assert_called_once_with(input_obj)

    @pytest.mark.asyncio
    async def test_start_child_workflow_with_node_id(
        self, mock_next_outbound, mock_payload_converter, node_id_dict, sample_node_id
    ):
        """Test start_child_workflow with node_id in args."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            input_obj = MagicMock(spec=StartChildWorkflowInput)
            input_obj.headers = {}
            input_obj.args = ("arg1", node_id_dict, "arg3")

            await interceptor.start_child_workflow(input_obj)

            # Verify node_id was added to headers
            assert NODE_ID_HEADER_KEY in input_obj.headers
            assert input_obj.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"

            # Verify node_id was removed from args
            assert input_obj.args == ("arg1", "arg3")

            # Verify next interceptor was called
            mock_next_outbound.start_child_workflow.assert_called_once_with(input_obj)

    @pytest.mark.asyncio
    async def test_start_child_workflow_without_node_id(self, mock_next_outbound):
        """Test start_child_workflow without node_id in args."""
        interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        input_obj = MagicMock(spec=StartChildWorkflowInput)
        input_obj.headers = {}
        original_args = ("arg1", "arg2", "arg3")
        input_obj.args = original_args

        await interceptor.start_child_workflow(input_obj)

        # Verify no headers were added
        assert NODE_ID_HEADER_KEY not in input_obj.headers

        # Verify args were not modified
        assert input_obj.args == original_args

        # Verify next interceptor was called
        mock_next_outbound.start_child_workflow.assert_called_once_with(input_obj)


# Tests for NodeIdInterceptor
class TestNodeIdInterceptor:
    def test_init_default_values(self):
        """Test interceptor initialization with default values."""
        interceptor = NodeIdInterceptor()

        assert interceptor.logger_module is None

    def test_init_custom_values(self):
        """Test interceptor initialization with custom values."""
        mock_logger = MagicMock()

        interceptor = NodeIdInterceptor(logger_module=mock_logger)

        assert interceptor.logger_module == mock_logger

    def test_workflow_interceptor_class(self):
        """Test workflow interceptor class creation."""
        interceptor = NodeIdInterceptor()

        input_obj = MagicMock(spec=WorkflowInterceptorClassInput)
        interceptor_class = interceptor.workflow_interceptor_class(input_obj)

        # Verify it returns a class
        assert callable(interceptor_class)

        # Create an instance and test it
        mock_next = MagicMock(spec=WorkflowInboundInterceptor)
        instance = interceptor_class(mock_next)

        # Verify it's an instance of WorkflowInboundInterceptor
        assert isinstance(instance, WorkflowInboundInterceptor)

        # Test the init method
        mock_outbound = MagicMock(spec=WorkflowOutboundInterceptor)
        instance.init(mock_outbound)

        # Verify init was called on next interceptor with NodeIdWorkflowOutboundInterceptor
        mock_next.init.assert_called_once()
        outbound_interceptor = mock_next.init.call_args[0][0]
        assert isinstance(outbound_interceptor, NodeIdWorkflowOutboundInterceptor)


# Integration tests
class TestNodeIdInterceptorIntegration:
    """Integration tests that test the complete flow of node_id handling."""

    def test_complete_activity_flow(self, mock_payload_converter, sample_node_id, node_id_dict):
        """Test the complete flow for activity execution with node_id."""
        # Create mock next interceptors
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)
        mock_next_outbound.start_activity = MagicMock()

        # Create outbound interceptor
        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        # Test activity start with node_id
        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            activity_input = MagicMock(spec=StartActivityInput)
            activity_input.headers = {}
            activity_input.args = ("activity_arg1", node_id_dict, "activity_arg2")

            outbound_interceptor.start_activity(activity_input)

            # Verify complete flow
            assert NODE_ID_HEADER_KEY in activity_input.headers
            assert activity_input.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"
            assert activity_input.args == ("activity_arg1", "activity_arg2")
            mock_next_outbound.start_activity.assert_called_once_with(activity_input)

    @pytest.mark.asyncio
    async def test_complete_child_workflow_flow(self, mock_payload_converter, sample_node_id, node_id_dict):
        """Test the complete flow for child workflow execution with node_id."""
        # Create mock next interceptors
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)
        mock_next_outbound.start_child_workflow = AsyncMock()

        # Create outbound interceptor
        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        # Test child workflow start with node_id
        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            child_input = MagicMock(spec=StartChildWorkflowInput)
            child_input.headers = {}
            child_input.args = ("workflow_arg1", node_id_dict, "workflow_arg2")

            await outbound_interceptor.start_child_workflow(child_input)

            # Verify complete flow
            assert NODE_ID_HEADER_KEY in child_input.headers
            assert child_input.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"
            assert child_input.args == ("workflow_arg1", "workflow_arg2")
            mock_next_outbound.start_child_workflow.assert_called_once_with(child_input)

    def test_workflow_interceptor_integration(self):
        """Test the integration of workflow interceptor creation and usage."""
        # Create main interceptor
        main_interceptor = NodeIdInterceptor()

        # Get the interceptor class
        input_obj = MagicMock(spec=WorkflowInterceptorClassInput)
        interceptor_class = main_interceptor.workflow_interceptor_class(input_obj)

        # Create instance
        mock_next_inbound = MagicMock(spec=WorkflowInboundInterceptor)
        inbound_instance = interceptor_class(mock_next_inbound)

        # Test initialization
        mock_outbound = MagicMock(spec=WorkflowOutboundInterceptor)
        inbound_instance.init(mock_outbound)

        # Verify the chain was set up correctly
        mock_next_inbound.init.assert_called_once()
        passed_outbound = mock_next_inbound.init.call_args[0][0]
        assert isinstance(passed_outbound, NodeIdWorkflowOutboundInterceptor)
        assert passed_outbound.next == mock_outbound

    def test_multiple_node_id_handling(self, mock_payload_converter):
        """Test handling of multiple node_id dicts in args."""
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            # Test with multiple node_id dicts - should take the first one
            activity_input = MagicMock(spec=StartActivityInput)
            activity_input.headers = {}
            activity_input.args = (
                "arg1",
                {"__temporal_node_id": "first_node"},
                "arg2",
                {"__temporal_node_id": "second_node"},
                "arg3",
            )

            outbound_interceptor.start_activity(activity_input)

            # Should use the first node_id found
            assert activity_input.headers[NODE_ID_HEADER_KEY] == "payload:first_node"
            # Should remove all node_id dicts
            assert activity_input.args == ("arg1", "arg2", "arg3")

    def test_edge_case_empty_args(self):
        """Test handling of empty args."""
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        activity_input = MagicMock(spec=StartActivityInput)
        activity_input.headers = {}
        activity_input.args = ()

        outbound_interceptor.start_activity(activity_input)

        # Should not add headers or modify args
        assert NODE_ID_HEADER_KEY not in activity_input.headers
        assert activity_input.args == ()
        mock_next_outbound.start_activity.assert_called_once()

    def test_edge_case_non_dict_args(self):
        """Test handling of args that are not dicts."""
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        activity_input = MagicMock(spec=StartActivityInput)
        activity_input.headers = {}
        activity_input.args = ("string_arg", 123, None, [1, 2, 3])

        outbound_interceptor.start_activity(activity_input)

        # Should not add headers or modify args
        assert NODE_ID_HEADER_KEY not in activity_input.headers
        assert activity_input.args == ("string_arg", 123, None, [1, 2, 3])
        mock_next_outbound.start_activity.assert_called_once()

    def test_header_key_constant(self):
        """Test that the NODE_ID_HEADER_KEY constant is correctly defined."""
        assert NODE_ID_HEADER_KEY == "node_id"

    def test_payload_conversion_integration(self, mock_payload_converter, sample_node_id, node_id_dict):
        """Test that payload conversion is properly integrated."""
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter) as mock_pc:
            activity_input = MagicMock(spec=StartActivityInput)
            activity_input.headers = {}
            activity_input.args = (node_id_dict,)

            outbound_interceptor.start_activity(activity_input)

            # Verify payload converter was called
            mock_pc.assert_called_once()
            mock_payload_converter.to_payload.assert_called_once_with(sample_node_id)

            # Verify the converted payload was used
            assert activity_input.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"


# Error handling tests
class TestNodeIdInterceptorErrorHandling:
    """Test error handling scenarios."""

    def test_payload_conversion_error(self, sample_node_id, node_id_dict):
        """Test handling of payload conversion errors."""
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        # Mock payload converter to raise an exception
        mock_converter = MagicMock()
        mock_converter.to_payload.side_effect = Exception("Conversion failed")

        with patch.object(workflow, "payload_converter", return_value=mock_converter):
            activity_input = MagicMock(spec=StartActivityInput)
            activity_input.headers = {}
            activity_input.args = (node_id_dict,)

            # Should not raise exception, but should still process the request
            with pytest.raises(Exception, match="Conversion failed"):
                outbound_interceptor.start_activity(activity_input)

    def test_missing_headers_attribute(self, mock_payload_converter, sample_node_id, node_id_dict):
        """Test handling when input object doesn't have headers attribute."""
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(mock_next_outbound)

        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            activity_input = MagicMock(spec=StartActivityInput)
            # Remove headers attribute
            delattr(activity_input, "headers")
            activity_input.args = (node_id_dict,)

            # Should not raise exception; code creates headers if missing
            outbound_interceptor.start_activity(activity_input)

            # Verify that headers were created and node_id was added
            assert hasattr(activity_input, "headers")
            assert activity_input.headers is not None
            assert NODE_ID_HEADER_KEY in activity_input.headers
            assert activity_input.headers[NODE_ID_HEADER_KEY] == f"payload:{sample_node_id}"
