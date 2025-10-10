import contextvars
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from temporalio import activity, workflow
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    ExecuteWorkflowInput,
    SignalChildWorkflowInput,
    SignalExternalWorkflowInput,
    StartActivityInput,
    StartChildWorkflowInput,
    StartLocalActivityInput,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
    WorkflowOutboundInterceptor,
)

from zamp_public_workflow_sdk.temporal.interceptors.tracing_interceptor import (
    TraceActivityInterceptor,
    TraceInterceptor,
    TraceWorkflowInboundInterceptor,
    TraceWorkflowOutboundInterceptor,
)


# Test fixtures
@pytest.fixture
def trace_context():
    """Create a context variable for testing."""
    return contextvars.ContextVar("test_trace_id", default=None)


@pytest.fixture
def context_bind_fn(trace_context):
    """Create a bind function for the context variable."""

    def _bind(**kwargs):
        for key, value in kwargs.items():
            if key == "test_trace_id":
                trace_context.set(value)

    return _bind


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger_module = MagicMock()
    logger_module.get_logger.return_value = logger
    return logger_module


@pytest.fixture
def mock_next_activity():
    """Create a mock for the next activity interceptor."""
    next_interceptor = MagicMock(spec=ActivityInboundInterceptor)
    next_interceptor.execute_activity = AsyncMock()
    return next_interceptor


@pytest.fixture
def mock_next_workflow_inbound():
    """Create a mock for the next workflow inbound interceptor."""
    next_interceptor = MagicMock(spec=WorkflowInboundInterceptor)
    next_interceptor.execute_workflow = AsyncMock()
    return next_interceptor


@pytest.fixture
def mock_next_workflow_outbound():
    """Create a mock for the next workflow outbound interceptor."""
    next_interceptor = MagicMock(spec=WorkflowOutboundInterceptor)
    next_interceptor.start_activity = MagicMock()
    next_interceptor.start_child_workflow = AsyncMock()
    next_interceptor.start_local_activity = MagicMock()
    next_interceptor.signal_child_workflow = AsyncMock()
    next_interceptor.signal_external_workflow = AsyncMock()
    return next_interceptor


@pytest.fixture
def mock_payload_converter():
    """Mock the payload converter."""
    converter = MagicMock()
    converter.to_payload.side_effect = lambda x: f"payload:{x}"
    converter.from_payload.side_effect = lambda p, _: p.replace("payload:", "")
    return converter


# Tests for TraceActivityInterceptor
class TestTraceActivityInterceptor:
    @pytest.mark.asyncio
    async def test_execute_activity_with_trace(
        self, mock_next_activity, context_bind_fn, trace_context, mock_payload_converter
    ):
        with patch.object(activity, "payload_converter", return_value=mock_payload_converter):
            interceptor = TraceActivityInterceptor(mock_next_activity, "X-Trace-ID", "test_trace_id", context_bind_fn)

            # Create input with trace header
            input_obj = MagicMock(spec=ExecuteActivityInput)
            input_obj.headers = {"X-Trace-ID": "payload:test-trace-123"}

            # Execute
            await interceptor.execute_activity(input_obj)

            # Verify context was set and next interceptor was called
            assert trace_context.get() == "test-trace-123"
            mock_next_activity.execute_activity.assert_called_once_with(input_obj)

    @pytest.mark.asyncio
    async def test_execute_activity_without_trace(self, mock_next_activity, context_bind_fn, trace_context):
        interceptor = TraceActivityInterceptor(mock_next_activity, "X-Trace-ID", "test_trace_id", context_bind_fn)

        # Create input without trace header
        input_obj = MagicMock(spec=ExecuteActivityInput)
        input_obj.headers = {}

        # Execute
        await interceptor.execute_activity(input_obj)

        # Verify context was not set and next interceptor was called
        assert trace_context.get() is None
        mock_next_activity.execute_activity.assert_called_once_with(input_obj)


# Tests for TraceWorkflowInboundInterceptor
class TestTraceWorkflowInboundInterceptor:
    def test_init(self, mock_next_workflow_inbound, context_bind_fn, mock_logger):
        outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        interceptor = TraceWorkflowInboundInterceptor(
            mock_next_workflow_inbound,
            "X-Trace-ID",
            "test_trace_id",
            context_bind_fn,
            mock_logger,
        )

        interceptor.init(outbound)

        # Verify outbound interceptor was initialized
        mock_next_workflow_inbound.init.assert_called_once()
        # The argument should be an instance of TraceWorkflowOutboundInterceptor
        outbound_interceptor = mock_next_workflow_inbound.init.call_args[0][0]
        assert isinstance(outbound_interceptor, TraceWorkflowOutboundInterceptor)

    @pytest.mark.asyncio
    async def test_execute_workflow_with_trace_header(
        self,
        mock_next_workflow_inbound,
        context_bind_fn,
        mock_logger,
        mock_payload_converter,
    ):
        with (
            patch.object(workflow, "payload_converter", return_value=mock_payload_converter),
            patch.object(workflow, "info", return_value=MagicMock(workflow_id="wf-123")),
            patch.object(
                workflow.unsafe,
                "sandbox_unrestricted",
                return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock()),
            ),
        ):
            interceptor = TraceWorkflowInboundInterceptor(
                mock_next_workflow_inbound,
                "X-Trace-ID",
                "test_trace_id",
                context_bind_fn,
                mock_logger,
            )

            # Create input with trace header
            input_obj = MagicMock(spec=ExecuteWorkflowInput)
            input_obj.headers = {"X-Trace-ID": "payload:trace-from-header-123"}

            # Execute
            await interceptor.execute_workflow(input_obj)

            # Verify trace ID was retrieved and stored
            assert interceptor.get_trace_id() == "trace-from-header-123"
            # Verify next interceptor was called
            mock_next_workflow_inbound.execute_workflow.assert_called_once_with(input_obj)

    @pytest.mark.asyncio
    async def test_execute_workflow_without_trace_header(
        self, mock_next_workflow_inbound, context_bind_fn, mock_logger
    ):
        with (
            patch.object(workflow, "info", return_value=MagicMock(workflow_id="wf-123")),
            patch.object(
                workflow.unsafe,
                "sandbox_unrestricted",
                return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock()),
            ),
        ):
            interceptor = TraceWorkflowInboundInterceptor(
                mock_next_workflow_inbound,
                "X-Trace-ID",
                "test_trace_id",
                context_bind_fn,
                mock_logger,
            )

            # Create input without trace header
            input_obj = MagicMock(spec=ExecuteWorkflowInput)
            input_obj.headers = {}

            # Execute
            await interceptor.execute_workflow(input_obj)

            # Verify workflow ID was used as trace ID
            assert interceptor.get_trace_id() == "wf-123"
            # Verify next interceptor was called
            mock_next_workflow_inbound.execute_workflow.assert_called_once_with(input_obj)

    @pytest.mark.asyncio
    async def test_execute_workflow_context_error(self, mock_next_workflow_inbound, mock_logger):
        with (
            patch.object(workflow, "info", return_value=MagicMock(workflow_id="wf-123")),
            patch.object(
                workflow.unsafe,
                "sandbox_unrestricted",
                return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock()),
            ),
        ):
            # Create a bind function that raises an exception
            def failing_bind(**kwargs):
                raise Exception("Context bind error")

            interceptor = TraceWorkflowInboundInterceptor(
                mock_next_workflow_inbound,
                "X-Trace-ID",
                "test_trace_id",
                failing_bind,
                mock_logger,
            )

            input_obj = MagicMock(spec=ExecuteWorkflowInput)
            input_obj.headers = {}

            # Execute should not raise the exception
            await interceptor.execute_workflow(input_obj)

            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Context bind error" in mock_logger.error.call_args[0][0]
            # Verify next interceptor was still called
            mock_next_workflow_inbound.execute_workflow.assert_called_once_with(input_obj)


# Tests for TraceWorkflowOutboundInterceptor
class TestTraceWorkflowOutboundInterceptor:
    def test_start_activity(self, mock_next_workflow_outbound, mock_payload_converter):
        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            # Mock get_trace_id function
            def get_trace_id():
                return "trace-id-123"

            interceptor = TraceWorkflowOutboundInterceptor(
                mock_next_workflow_outbound, "X-Trace-ID", "test_trace_id", get_trace_id
            )

            # Create input for starting activity
            input_obj = MagicMock(spec=StartActivityInput)
            input_obj.headers = {}

            # Execute
            interceptor.start_activity(input_obj)

            # Verify trace header was added
            assert "X-Trace-ID" in input_obj.headers
            assert input_obj.headers["X-Trace-ID"] == "payload:trace-id-123"
            # Verify next interceptor was called
            mock_next_workflow_outbound.start_activity.assert_called_once_with(input_obj)

    @pytest.mark.asyncio
    async def test_start_child_workflow(self, mock_next_workflow_outbound, mock_payload_converter):
        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            # Mock get_trace_id function
            def get_trace_id():
                return "trace-id-123"

            interceptor = TraceWorkflowOutboundInterceptor(
                mock_next_workflow_outbound, "X-Trace-ID", "test_trace_id", get_trace_id
            )

            # Create input for starting child workflow
            input_obj = MagicMock(spec=StartChildWorkflowInput)
            input_obj.headers = {}
            input_obj.memo = None  # Add memo attribute to prevent AttributeError
            input_obj.parent_close_policy = workflow.ParentClosePolicy.TERMINATE

            # Execute
            await interceptor.start_child_workflow(input_obj)

            # Verify trace header was added
            assert "X-Trace-ID" in input_obj.headers
            assert input_obj.headers["X-Trace-ID"] == "payload:trace-id-123"
            # Verify next interceptor was called
            mock_next_workflow_outbound.start_child_workflow.assert_called_once_with(input_obj)

    def test_start_local_activity(self, mock_next_workflow_outbound, mock_payload_converter):
        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            # Mock get_trace_id function
            def get_trace_id():
                return "trace-id-123"

            interceptor = TraceWorkflowOutboundInterceptor(
                mock_next_workflow_outbound, "X-Trace-ID", "test_trace_id", get_trace_id
            )

            # Create input for starting local activity
            input_obj = MagicMock(spec=StartLocalActivityInput)
            input_obj.headers = {}

            # Execute
            interceptor.start_local_activity(input_obj)

            # Verify trace header was added
            assert "X-Trace-ID" in input_obj.headers
            assert input_obj.headers["X-Trace-ID"] == "payload:trace-id-123"
            # Verify next interceptor was called
            mock_next_workflow_outbound.start_local_activity.assert_called_once_with(input_obj)

    @pytest.mark.asyncio
    async def test_signal_child_workflow(self, mock_next_workflow_outbound, mock_payload_converter):
        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            # Mock get_trace_id function
            def get_trace_id():
                return "trace-id-123"

            interceptor = TraceWorkflowOutboundInterceptor(
                mock_next_workflow_outbound, "X-Trace-ID", "test_trace_id", get_trace_id
            )

            # Create input for signaling child workflow
            input_obj = MagicMock(spec=SignalChildWorkflowInput)
            input_obj.headers = {}

            # Execute
            await interceptor.signal_child_workflow(input_obj)

            # Verify trace header was added
            assert "X-Trace-ID" in input_obj.headers
            assert input_obj.headers["X-Trace-ID"] == "payload:trace-id-123"
            # Verify next interceptor was called
            mock_next_workflow_outbound.signal_child_workflow.assert_called_once_with(input_obj)

    @pytest.mark.asyncio
    async def test_signal_external_workflow(self, mock_next_workflow_outbound, mock_payload_converter):
        with patch.object(workflow, "payload_converter", return_value=mock_payload_converter):
            # Mock get_trace_id function
            def get_trace_id():
                return "trace-id-123"

            interceptor = TraceWorkflowOutboundInterceptor(
                mock_next_workflow_outbound, "X-Trace-ID", "test_trace_id", get_trace_id
            )

            # Create input for signaling external workflow
            input_obj = MagicMock(spec=SignalExternalWorkflowInput)
            input_obj.headers = {}

            # Execute
            await interceptor.signal_external_workflow(input_obj)

            # Verify trace header was added
            assert "X-Trace-ID" in input_obj.headers
            assert input_obj.headers["X-Trace-ID"] == "payload:trace-id-123"
            # Verify next interceptor was called
            mock_next_workflow_outbound.signal_external_workflow.assert_called_once_with(input_obj)


# Tests for TraceInterceptor
class TestTraceInterceptor:
    def test_intercept_activity(self, context_bind_fn, mock_logger, mock_next_activity):
        interceptor = TraceInterceptor("X-Trace-ID", "test_trace_id", mock_logger, context_bind_fn)

        result = interceptor.intercept_activity(mock_next_activity)

        assert isinstance(result, TraceActivityInterceptor)
        assert result.trace_header_key == "X-Trace-ID"
        assert result.trace_context_key == "test_trace_id"

    def test_workflow_interceptor_class(self, context_bind_fn, mock_logger):
        interceptor = TraceInterceptor("X-Trace-ID", "test_trace_id", mock_logger, context_bind_fn)

        input_obj = MagicMock(spec=WorkflowInterceptorClassInput)
        factory = interceptor.workflow_interceptor_class(input_obj)

        # Create a workflow interceptor using the factory
        mock_next = MagicMock(spec=WorkflowInboundInterceptor)
        result = factory(mock_next)

        assert isinstance(result, TraceWorkflowInboundInterceptor)
        assert result.trace_header_key == "X-Trace-ID"
        assert result.trace_context_key == "test_trace_id"
        assert result.context_bind_fn == context_bind_fn

    def test_bind_trace_context(self, context_bind_fn, mock_logger, trace_context):
        interceptor = TraceInterceptor("X-Trace-ID", "test_trace_id", mock_logger, context_bind_fn)

        # Initially context should be None
        assert trace_context.get() is None

        # Bind a trace ID
        interceptor.bind_trace_context("manual-trace-123")

        # Context should now have the trace ID
        assert trace_context.get() == "manual-trace-123"

    def test_generate_trace_id(self, context_bind_fn, mock_logger):
        interceptor = TraceInterceptor("X-Trace-ID", "test_trace_id", mock_logger, context_bind_fn)

        # Generate a trace ID and verify it's a valid UUID
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            trace_id = interceptor.generate_trace_id()
            assert trace_id == "12345678-1234-5678-1234-567812345678"
