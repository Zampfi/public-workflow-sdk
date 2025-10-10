"""
Integration tests for NodeIdInterceptor.

This module contains integration tests that demonstrate the complete flow
of node_id handling from workflow to activities using the NodeIdInterceptor.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


from temporalio import workflow
from temporalio.worker import (
    StartActivityInput,
    StartChildWorkflowInput,
    WorkflowInboundInterceptor,
    WorkflowOutboundInterceptor,
)

from zamp_public_workflow_sdk.temporal.interceptors.node_id_interceptor import (
    NODE_ID_HEADER_KEY,
    NodeIdInterceptor,
    NodeIdWorkflowOutboundInterceptor,
)


class TestNodeIdInterceptorIntegration:
    """Integration tests for the complete node_id flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_node_id = "integration_test_action#instance_456"
        self.node_id_dict = {"__temporal_node_id": self.sample_node_id}

    def test_end_to_end_activity_flow(self):
        """Test the complete end-to-end flow for activity execution."""
        # Create the main interceptor
        main_interceptor = NodeIdInterceptor()

        # Get the workflow interceptor class
        interceptor_class = main_interceptor.workflow_interceptor_class(MagicMock())

        # Create the workflow inbound interceptor
        mock_next_inbound = MagicMock(spec=WorkflowInboundInterceptor)
        inbound_interceptor = interceptor_class(mock_next_inbound)

        # Create mock outbound interceptor
        mock_outbound = MagicMock(spec=WorkflowOutboundInterceptor)
        mock_outbound.start_activity = MagicMock()

        # Initialize the inbound interceptor
        inbound_interceptor.init(mock_outbound)

        # Get the NodeIdWorkflowOutboundInterceptor that was created
        outbound_interceptor = mock_next_inbound.init.call_args[0][0]
        assert isinstance(outbound_interceptor, NodeIdWorkflowOutboundInterceptor)

        # Mock payload converter
        mock_converter = MagicMock()
        mock_converter.to_payload.return_value = f"payload:{self.sample_node_id}"

        with patch.object(workflow, "payload_converter", return_value=mock_converter):
            # Create activity input with node_id
            activity_input = MagicMock(spec=StartActivityInput)
            activity_input.headers = {}
            activity_input.args = ("param1", self.node_id_dict, "param2")

            # Execute the activity start
            outbound_interceptor.start_activity(activity_input)

            # Verify the complete flow
            # 1. Node ID should be extracted and added to headers
            assert NODE_ID_HEADER_KEY in activity_input.headers
            assert activity_input.headers[NODE_ID_HEADER_KEY] == f"payload:{self.sample_node_id}"

            # 2. Node ID dict should be removed from args
            assert activity_input.args == ("param1", "param2")

            # 3. Next interceptor should be called
            mock_outbound.start_activity.assert_called_once_with(activity_input)

    @pytest.mark.asyncio
    async def test_end_to_end_child_workflow_flow(self):
        """Test the complete end-to-end flow for child workflow execution."""
        # Create the main interceptor
        main_interceptor = NodeIdInterceptor()

        # Get the workflow interceptor class
        interceptor_class = main_interceptor.workflow_interceptor_class(MagicMock())

        # Create the workflow inbound interceptor
        mock_next_inbound = MagicMock(spec=WorkflowInboundInterceptor)
        inbound_interceptor = interceptor_class(mock_next_inbound)

        # Create mock outbound interceptor
        mock_outbound = MagicMock(spec=WorkflowOutboundInterceptor)
        mock_outbound.start_child_workflow = AsyncMock()

        # Initialize the inbound interceptor
        inbound_interceptor.init(mock_outbound)

        # Get the NodeIdWorkflowOutboundInterceptor that was created
        outbound_interceptor = mock_next_inbound.init.call_args[0][0]
        assert isinstance(outbound_interceptor, NodeIdWorkflowOutboundInterceptor)

        # Mock payload converter
        mock_converter = MagicMock()
        mock_converter.to_payload.return_value = f"payload:{self.sample_node_id}"

        with patch.object(workflow, "payload_converter", return_value=mock_converter):
            # Create child workflow input with node_id
            child_input = MagicMock(spec=StartChildWorkflowInput)
            child_input.headers = {}
            child_input.args = ("workflow_param1", self.node_id_dict, "workflow_param2")

            # Execute the child workflow start
            await outbound_interceptor.start_child_workflow(child_input)

            # Verify the complete flow
            # 1. Node ID should be extracted and added to headers
            assert NODE_ID_HEADER_KEY in child_input.headers
            assert child_input.headers[NODE_ID_HEADER_KEY] == f"payload:{self.sample_node_id}"

            # 2. Node ID dict should be removed from args
            assert child_input.args == ("workflow_param1", "workflow_param2")

            # 3. Next interceptor should be called
            mock_outbound.start_child_workflow.assert_called_once_with(child_input)

    def test_interceptor_chain_creation(self):
        """Test that the interceptor chain is created correctly."""
        # Create main interceptor with custom header key
        custom_header_key = "custom_node_id_key"
        main_interceptor = NodeIdInterceptor(node_id_header_key=custom_header_key)

        # Create the interceptor chain
        interceptor_class = main_interceptor.workflow_interceptor_class(MagicMock())
        mock_next_inbound = MagicMock(spec=WorkflowInboundInterceptor)
        inbound_interceptor = interceptor_class(mock_next_inbound)

        # Test initialization
        mock_outbound = MagicMock(spec=WorkflowOutboundInterceptor)
        inbound_interceptor.init(mock_outbound)

        # Verify the outbound interceptor was created correctly
        mock_next_inbound.init.assert_called_once()
        created_outbound = mock_next_inbound.init.call_args[0][0]
        assert isinstance(created_outbound, NodeIdWorkflowOutboundInterceptor)
        assert created_outbound.node_id_header_key == NODE_ID_HEADER_KEY  # Should use constant, not custom
        assert created_outbound.next == mock_outbound

    def test_multiple_activities_in_sequence(self):
        """Test handling multiple activities with different node_ids."""
        main_interceptor = NodeIdInterceptor()

        # Create outbound interceptor directly for testing
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)
        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(
            mock_next_outbound, main_interceptor.node_id_header_key
        )

        mock_converter = MagicMock()
        mock_converter.to_payload.side_effect = lambda x: f"payload:{x}"

        with patch.object(workflow, "payload_converter", return_value=mock_converter):
            # First activity
            activity1_input = MagicMock(spec=StartActivityInput)
            activity1_input.headers = {}
            activity1_input.args = ({"__temporal_node_id": "action1#instance1"},)

            outbound_interceptor.start_activity(activity1_input)

            assert activity1_input.headers[NODE_ID_HEADER_KEY] == "payload:action1#instance1"
            assert activity1_input.args == ()

            # Second activity
            activity2_input = MagicMock(spec=StartActivityInput)
            activity2_input.headers = {}
            activity2_input.args = (
                "param",
                {"__temporal_node_id": "action2#instance2"},
            )

            outbound_interceptor.start_activity(activity2_input)

            assert activity2_input.headers[NODE_ID_HEADER_KEY] == "payload:action2#instance2"
            assert activity2_input.args == ("param",)

    def test_mixed_activities_and_child_workflows(self):
        """Test handling both activities and child workflows."""
        main_interceptor = NodeIdInterceptor()
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)
        mock_next_outbound.start_activity = MagicMock()
        mock_next_outbound.start_child_workflow = AsyncMock()

        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(
            mock_next_outbound, main_interceptor.node_id_header_key
        )

        mock_converter = MagicMock()
        mock_converter.to_payload.side_effect = lambda x: f"payload:{x}"

        with patch.object(workflow, "payload_converter", return_value=mock_converter):
            # Activity execution
            activity_input = MagicMock(spec=StartActivityInput)
            activity_input.headers = {}
            activity_input.args = ({"__temporal_node_id": "activity_node"},)

            outbound_interceptor.start_activity(activity_input)

            # Child workflow execution
            child_input = MagicMock(spec=StartChildWorkflowInput)
            child_input.headers = {}
            child_input.args = ({"__temporal_node_id": "workflow_node"},)

            # This should work in a real async context, but for testing we'll call directly
            import asyncio

            async def test_async():
                await outbound_interceptor.start_child_workflow(child_input)

            # Run the async test
            if hasattr(asyncio, "run"):
                asyncio.run(test_async())
            else:
                # Fallback for older Python versions
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(test_async())
                finally:
                    loop.close()

            # Verify both were handled correctly
            assert activity_input.headers[NODE_ID_HEADER_KEY] == "payload:activity_node"
            assert activity_input.args == ()

            assert child_input.headers[NODE_ID_HEADER_KEY] == "payload:workflow_node"
            assert child_input.args == ()

            # Verify both next interceptors were called
            mock_next_outbound.start_activity.assert_called_once()
            mock_next_outbound.start_child_workflow.assert_called_once()

    def test_no_node_id_handling(self):
        """Test that requests without node_id are handled normally."""
        main_interceptor = NodeIdInterceptor()
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(
            mock_next_outbound, main_interceptor.node_id_header_key
        )

        # Activity without node_id
        activity_input = MagicMock(spec=StartActivityInput)
        activity_input.headers = {}
        original_args = ("param1", "param2", {"other": "dict"})
        activity_input.args = original_args

        outbound_interceptor.start_activity(activity_input)

        # Should not modify headers or args
        assert NODE_ID_HEADER_KEY not in activity_input.headers
        assert activity_input.args == original_args
        mock_next_outbound.start_activity.assert_called_once()

    def test_malformed_node_id_dict(self):
        """Test handling of malformed node_id dictionaries."""
        main_interceptor = NodeIdInterceptor()
        mock_next_outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        outbound_interceptor = NodeIdWorkflowOutboundInterceptor(
            mock_next_outbound, main_interceptor.node_id_header_key
        )

        # Dict with extra keys (should be ignored)
        activity_input = MagicMock(spec=StartActivityInput)
        activity_input.headers = {}
        malformed_dict = {"__temporal_node_id": "test", "extra_key": "extra_value"}
        activity_input.args = ("param1", malformed_dict, "param2")

        outbound_interceptor.start_activity(activity_input)

        # Should not extract node_id from malformed dict
        assert NODE_ID_HEADER_KEY not in activity_input.headers
        # Should not filter out the malformed dict
        assert activity_input.args == ("param1", malformed_dict, "param2")

    def test_custom_logger_integration(self):
        """Test that custom logger is properly stored."""
        mock_logger = MagicMock()
        main_interceptor = NodeIdInterceptor(logger_module=mock_logger)

        assert main_interceptor.logger_module == mock_logger

    def test_node_id_header_constant(self):
        """Test that the NODE_ID_HEADER_KEY constant is correct."""
        assert NODE_ID_HEADER_KEY == "node_id"

        # Test that interceptor uses the constant
        interceptor = NodeIdInterceptor()
        assert interceptor.node_id_header_key == NODE_ID_HEADER_KEY
