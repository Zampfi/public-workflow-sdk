"""
Unit and integration tests for SentryInterceptor.

This module contains comprehensive tests for the SentryInterceptor, including:
- Unit tests for individual interceptor classes
- Tests for retry count logic (only report when attempt > 5)
- Error handling and edge case testing
- Context extraction testing
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from temporalio import activity, workflow
from temporalio.worker import (
    ActivityInboundInterceptor,
    ActivityOutboundInterceptor,
    ExecuteActivityInput,
    ExecuteWorkflowInput,
    Interceptor,
    StartChildWorkflowInput,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
    WorkflowOutboundInterceptor,
)

from zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor import (
    SentryActivityInboundInterceptor,
    SentryActivityOutboundInterceptor,
    SentryInterceptor,
    SentryWorkflowInboundInterceptor,
    SentryWorkflowOutboundInterceptor,
    extract_context_from_contextvars,
)


# Test fixtures
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
def mock_next_activity_outbound():
    """Create a mock for the next activity outbound interceptor."""
    next_interceptor = MagicMock(spec=ActivityOutboundInterceptor)
    next_interceptor.execute_activity = AsyncMock()
    return next_interceptor


@pytest.fixture
def mock_next_workflow_inbound():
    """Create a mock for the next workflow inbound interceptor."""
    next_interceptor = MagicMock(spec=WorkflowInboundInterceptor)
    next_interceptor.execute_workflow = AsyncMock()
    next_interceptor.start_child_workflow = AsyncMock()
    next_interceptor.init = MagicMock()
    return next_interceptor


@pytest.fixture
def mock_next_workflow_outbound():
    """Create a mock for the next workflow outbound interceptor."""
    next_interceptor = MagicMock(spec=WorkflowOutboundInterceptor)
    next_interceptor.execute_workflow = AsyncMock()
    next_interceptor.start_child_workflow = AsyncMock()
    return next_interceptor


@pytest.fixture
def mock_activity_input():
    """Create a mock ExecuteActivityInput."""
    input_obj = MagicMock(spec=ExecuteActivityInput)
    input_obj.fn = MagicMock()
    input_obj.fn.__name__ = "test_activity"
    input_obj.headers = {}
    input_obj.args = ("arg1", "arg2")
    return input_obj


@pytest.fixture
def mock_workflow_input():
    """Create a mock ExecuteWorkflowInput."""
    input_obj = MagicMock(spec=ExecuteWorkflowInput)
    input_obj.type = MagicMock()
    input_obj.type.__name__ = "TestWorkflow"
    input_obj.headers = {}
    input_obj.args = ("arg1", "arg2")
    return input_obj


# Tests for extract_context_from_contextvars
class TestExtractContextFromContextvars:
    def test_extract_context_no_function(self):
        """Test context extraction when no function is provided."""
        tags, context = extract_context_from_contextvars(None)
        assert tags == {}
        assert context == {}

    def test_extract_context_with_function(self):
        """Test context extraction with a function."""
        def context_fn():
            return {
                "user_id": "user123",
                "organization_id": "org456",
                "process_id": "proc789",
                "pantheon_trace_id": "trace123",
            }

        tags, context = extract_context_from_contextvars(context_fn)
        assert tags["user_id"] == "user123"
        assert tags["organization_id"] == "org456"
        assert tags["process_id"] == "proc789"
        assert tags["pantheon_trace_id"] == "trace123"
        assert context["user_id"] == "user123"
        assert context["organization_id"] == "org456"

    def test_extract_context_partial_data(self):
        """Test context extraction with partial data."""
        def context_fn():
            return {"user_id": "user123"}

        tags, context = extract_context_from_contextvars(context_fn)
        assert tags["user_id"] == "user123"
        assert context["user_id"] == "user123"
        assert "organization_id" not in tags

    def test_extract_context_function_error(self):
        """Test context extraction when function raises error."""
        def failing_context_fn():
            raise Exception("Context error")

        tags, context = extract_context_from_contextvars(failing_context_fn)
        # Should return empty dicts on error
        assert tags == {}
        assert context == {}


# Tests for SentryActivityInboundInterceptor
class TestSentryActivityInboundInterceptor:
    @pytest.mark.asyncio
    async def test_execute_activity_success(self, mock_next_activity, mock_logger, mock_activity_input):
        """Test successful activity execution doesn't report to Sentry."""
        interceptor = SentryActivityInboundInterceptor(mock_next_activity, mock_logger.get_logger(__name__))
        mock_next_activity.execute_activity.return_value = "success"

        result = await interceptor.execute_activity(mock_activity_input)

        assert result == "success"
        mock_next_activity.execute_activity.assert_called_once_with(mock_activity_input)

    @pytest.mark.asyncio
    async def test_execute_activity_failure_attempt_1_no_report(
        self, mock_next_activity, mock_logger, mock_activity_input
    ):
        """Test that activity failure on attempt 1 doesn't report to Sentry."""
        interceptor = SentryActivityInboundInterceptor(mock_next_activity, mock_logger.get_logger(__name__))
        test_exception = Exception("Test error")
        mock_next_activity.execute_activity.side_effect = test_exception

        # Mock activity.info() to return attempt 1
        mock_activity_info = MagicMock()
        mock_activity_info.attempt = 1

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
        ):
            with pytest.raises(Exception, match="Test error"):
                await interceptor.execute_activity(mock_activity_input)

            # Should not capture exception for attempt 1
            mock_capture.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_activity_failure_attempt_5_no_report(
        self, mock_next_activity, mock_logger, mock_activity_input
    ):
        """Test that activity failure on attempt 5 doesn't report to Sentry."""
        interceptor = SentryActivityInboundInterceptor(mock_next_activity, mock_logger.get_logger(__name__))
        test_exception = Exception("Test error")
        mock_next_activity.execute_activity.side_effect = test_exception

        # Mock activity.info() to return attempt 5
        mock_activity_info = MagicMock()
        mock_activity_info.attempt = 5

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
        ):
            with pytest.raises(Exception, match="Test error"):
                await interceptor.execute_activity(mock_activity_input)

            # Should not capture exception for attempt 5
            mock_capture.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_activity_failure_attempt_6_reports(
        self, mock_next_activity, mock_logger, mock_activity_input
    ):
        """Test that activity failure on attempt 6 reports to Sentry."""
        interceptor = SentryActivityInboundInterceptor(mock_next_activity, mock_logger.get_logger(__name__))
        test_exception = Exception("Test error")
        mock_next_activity.execute_activity.side_effect = test_exception

        # Mock activity.info() to return attempt 6
        mock_activity_info = MagicMock()
        mock_activity_info.attempt = 6

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope.return_value.__enter__.return_value = MagicMock()

            with pytest.raises(Exception, match="Test error"):
                await interceptor.execute_activity(mock_activity_input)

            # Should capture exception for attempt 6
            mock_capture.assert_called_once_with(test_exception)

    @pytest.mark.asyncio
    async def test_execute_activity_failure_attempt_10_reports(
        self, mock_next_activity, mock_logger, mock_activity_input
    ):
        """Test that activity failure on attempt 10 reports to Sentry."""
        interceptor = SentryActivityInboundInterceptor(mock_next_activity, mock_logger.get_logger(__name__))
        test_exception = Exception("Test error")
        mock_next_activity.execute_activity.side_effect = test_exception

        # Mock activity.info() to return attempt 10
        mock_activity_info = MagicMock()
        mock_activity_info.attempt = 10

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope.return_value.__enter__.return_value = MagicMock()

            with pytest.raises(Exception, match="Test error"):
                await interceptor.execute_activity(mock_activity_input)

            # Should capture exception for attempt 10
            mock_capture.assert_called_once_with(test_exception)

    @pytest.mark.asyncio
    async def test_execute_activity_failure_activity_info_error(
        self, mock_next_activity, mock_logger, mock_activity_input
    ):
        """Test that when activity.info() fails, it defaults to attempt 1 and doesn't report."""
        interceptor = SentryActivityInboundInterceptor(mock_next_activity, mock_logger.get_logger(__name__))
        test_exception = Exception("Test error")
        mock_next_activity.execute_activity.side_effect = test_exception

        with (
            patch.object(activity, "info", side_effect=Exception("Info error")),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
        ):
            with pytest.raises(Exception, match="Test error"):
                await interceptor.execute_activity(mock_activity_input)

            # Should not capture exception when activity.info() fails (defaults to attempt 1)
            mock_capture.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_activity_failure_with_context_extraction(
        self, mock_next_activity, mock_logger, mock_activity_input
    ):
        """Test activity failure with context extraction function."""
        def context_fn():
            return {"user_id": "user123", "organization_id": "org456"}

        interceptor = SentryActivityInboundInterceptor(
            mock_next_activity, mock_logger.get_logger(__name__), context_extraction_fn=context_fn
        )
        test_exception = Exception("Test error")
        mock_next_activity.execute_activity.side_effect = test_exception

        mock_activity_info = MagicMock()
        mock_activity_info.attempt = 6

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope_obj = MagicMock()
            mock_scope.return_value.__enter__.return_value = mock_scope_obj

            with pytest.raises(Exception, match="Test error"):
                await interceptor.execute_activity(mock_activity_input)

            # Verify context was set
            assert mock_scope_obj.set_tag.call_count >= 2  # At least user_id and organization_id
            mock_capture.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_activity_failure_sentry_capture_error(
        self, mock_next_activity, mock_logger, mock_activity_input
    ):
        """Test that Sentry capture errors are logged but don't prevent exception propagation."""
        interceptor = SentryActivityInboundInterceptor(mock_next_activity, mock_logger.get_logger(__name__))
        test_exception = Exception("Test error")
        mock_next_activity.execute_activity.side_effect = test_exception

        mock_activity_info = MagicMock()
        mock_activity_info.attempt = 6

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception", side_effect=Exception("Sentry error")),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope.return_value.__enter__.return_value = MagicMock()

            with pytest.raises(Exception, match="Test error"):
                await interceptor.execute_activity(mock_activity_input)

            # Should log the Sentry error
            mock_logger.get_logger(__name__).error.assert_called_once()


# Tests for SentryActivityOutboundInterceptor
class TestSentryActivityOutboundInterceptor:
    @pytest.mark.asyncio
    async def test_execute_activity_success(self, mock_next_activity_outbound, mock_logger, mock_activity_input):
        """Test successful activity execution doesn't report to Sentry."""
        interceptor = SentryActivityOutboundInterceptor(mock_next_activity_outbound, mock_logger.get_logger(__name__))
        mock_next_activity_outbound.execute_activity.return_value = "success"

        result = await interceptor.execute_activity(mock_activity_input)

        assert result == "success"
        mock_next_activity_outbound.execute_activity.assert_called_once_with(mock_activity_input)

    @pytest.mark.asyncio
    async def test_execute_activity_failure_attempt_1_no_report(
        self, mock_next_activity_outbound, mock_logger, mock_activity_input
    ):
        """Test that activity failure on attempt 1 doesn't report to Sentry."""
        interceptor = SentryActivityOutboundInterceptor(mock_next_activity_outbound, mock_logger.get_logger(__name__))
        test_exception = Exception("Test error")
        mock_next_activity_outbound.execute_activity.side_effect = test_exception

        mock_activity_info = MagicMock()
        mock_activity_info.attempt = 1

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
        ):
            with pytest.raises(Exception, match="Test error"):
                await interceptor.execute_activity(mock_activity_input)

            mock_capture.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_activity_failure_attempt_6_reports(
        self, mock_next_activity_outbound, mock_logger, mock_activity_input
    ):
        """Test that activity failure on attempt 6 reports to Sentry."""
        interceptor = SentryActivityOutboundInterceptor(mock_next_activity_outbound, mock_logger.get_logger(__name__))
        test_exception = Exception("Test error")
        mock_next_activity_outbound.execute_activity.side_effect = test_exception

        mock_activity_info = MagicMock()
        mock_activity_info.attempt = 6

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope.return_value.__enter__.return_value = MagicMock()

            with pytest.raises(Exception, match="Test error"):
                await interceptor.execute_activity(mock_activity_input)

            mock_capture.assert_called_once_with(test_exception)


# Tests for SentryWorkflowInboundInterceptor
class TestSentryWorkflowInboundInterceptor:
    def test_init(self, mock_next_workflow_inbound, mock_logger):
        """Test interceptor initialization."""
        interceptor = SentryWorkflowInboundInterceptor(
            mock_next_workflow_inbound, mock_logger.get_logger(__name__)
        )
        mock_outbound = MagicMock(spec=WorkflowOutboundInterceptor)

        interceptor.init(mock_outbound)

        mock_next_workflow_inbound.init.assert_called_once()
        outbound_interceptor = mock_next_workflow_inbound.init.call_args[0][0]
        assert isinstance(outbound_interceptor, SentryWorkflowOutboundInterceptor)

    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, mock_next_workflow_inbound, mock_logger, mock_workflow_input):
        """Test successful workflow execution doesn't report to Sentry."""
        interceptor = SentryWorkflowInboundInterceptor(
            mock_next_workflow_inbound, mock_logger.get_logger(__name__)
        )
        mock_next_workflow_inbound.execute_workflow.return_value = "success"

        result = await interceptor.execute_workflow(mock_workflow_input)

        assert result == "success"
        mock_next_workflow_inbound.execute_workflow.assert_called_once_with(mock_workflow_input)

    @pytest.mark.asyncio
    async def test_execute_workflow_failure_reports(
        self, mock_next_workflow_inbound, mock_logger, mock_workflow_input
    ):
        """Test that workflow failures always report to Sentry (no retry count check)."""
        interceptor = SentryWorkflowInboundInterceptor(
            mock_next_workflow_inbound, mock_logger.get_logger(__name__)
        )
        test_exception = Exception("Workflow error")
        mock_next_workflow_inbound.execute_workflow.side_effect = test_exception

        with (
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope.return_value.__enter__.return_value = MagicMock()

            with pytest.raises(Exception, match="Workflow error"):
                await interceptor.execute_workflow(mock_workflow_input)

            # Workflows should always report (no retry count check)
            mock_capture.assert_called_once_with(test_exception)

    @pytest.mark.asyncio
    async def test_start_child_workflow_failure_reports(
        self, mock_next_workflow_inbound, mock_logger
    ):
        """Test that child workflow failures always report to Sentry."""
        interceptor = SentryWorkflowInboundInterceptor(
            mock_next_workflow_inbound, mock_logger.get_logger(__name__)
        )
        test_exception = Exception("Child workflow error")
        mock_next_workflow_inbound.start_child_workflow.side_effect = test_exception

        input_obj = MagicMock(spec=StartChildWorkflowInput)
        input_obj.workflow = "ChildWorkflow"
        input_obj.headers = {}
        input_obj.args = ()

        with (
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope.return_value.__enter__.return_value = MagicMock()

            with pytest.raises(Exception, match="Child workflow error"):
                await interceptor.start_child_workflow(input_obj)

            # Child workflows should always report
            mock_capture.assert_called_once_with(test_exception)


# Tests for SentryWorkflowOutboundInterceptor
class TestSentryWorkflowOutboundInterceptor:
    @pytest.mark.asyncio
    async def test_execute_workflow_failure_reports(
        self, mock_next_workflow_outbound, mock_logger, mock_workflow_input
    ):
        """Test that workflow failures always report to Sentry."""
        interceptor = SentryWorkflowOutboundInterceptor(
            mock_next_workflow_outbound, mock_logger.get_logger(__name__)
        )
        test_exception = Exception("Workflow error")
        mock_next_workflow_outbound.execute_workflow.side_effect = test_exception

        with (
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope.return_value.__enter__.return_value = MagicMock()

            with pytest.raises(Exception, match="Workflow error"):
                await interceptor.execute_workflow(mock_workflow_input)

            mock_capture.assert_called_once_with(test_exception)


# Tests for SentryInterceptor
class TestSentryInterceptor:
    def test_init_without_dsn(self, mock_logger):
        """Test interceptor initialization without DSN."""
        with patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.init") as mock_init:
            interceptor = SentryInterceptor(mock_logger)

            assert interceptor.logger == mock_logger.get_logger(__name__)
            # Should not initialize Sentry if no DSN provided
            mock_init.assert_not_called()

    def test_init_with_dsn(self, mock_logger):
        """Test interceptor initialization with DSN."""
        with patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.init") as mock_init:
            interceptor = SentryInterceptor(mock_logger, sentry_dsn="test-dsn", environment="test")

            mock_init.assert_called_once_with(dsn="test-dsn", environment="test")

    def test_intercept_activity(self, mock_logger, mock_next_activity):
        """Test activity interceptor creation."""
        interceptor = SentryInterceptor(mock_logger)

        result = interceptor.intercept_activity(mock_next_activity)

        assert isinstance(result, SentryActivityInboundInterceptor)
        assert result.next == mock_next_activity
        assert result.logger == mock_logger.get_logger(__name__)

    def test_workflow_interceptor_class(self, mock_logger):
        """Test workflow interceptor class creation."""
        interceptor = SentryInterceptor(mock_logger)

        input_obj = MagicMock(spec=WorkflowInterceptorClassInput)
        factory = interceptor.workflow_interceptor_class(input_obj)

        # Create a workflow interceptor using the factory
        mock_next = MagicMock(spec=WorkflowInboundInterceptor)
        result = factory(mock_next)

        assert isinstance(result, SentryWorkflowInboundInterceptor)
        assert result.next == mock_next
        assert result.logger == mock_logger.get_logger(__name__)

    def test_init_with_context_extraction_fn(self, mock_logger):
        """Test interceptor initialization with context extraction function."""
        def context_fn():
            return {"user_id": "user123"}

        interceptor = SentryInterceptor(mock_logger, context_extraction_fn=context_fn)

        assert interceptor.context_extraction_fn == context_fn

    def test_init_with_additional_context_fn(self, mock_logger):
        """Test interceptor initialization with additional context function."""
        def additional_context_fn(input):
            return {"custom": "context"}

        interceptor = SentryInterceptor(mock_logger, additional_context_fn=additional_context_fn)

        assert interceptor.additional_context_fn == additional_context_fn


# Integration tests
class TestSentryInterceptorIntegration:
    """Integration tests for the complete Sentry interceptor flow."""

    @pytest.mark.asyncio
    async def test_activity_retry_count_threshold(self, mock_logger):
        """Test the complete flow of activity retry count threshold."""
        mock_next = MagicMock(spec=ActivityInboundInterceptor)
        mock_next.execute_activity = AsyncMock(side_effect=Exception("Activity error"))

        interceptor = SentryInterceptor(mock_logger)
        activity_interceptor = interceptor.intercept_activity(mock_next)

        input_obj = MagicMock(spec=ExecuteActivityInput)
        input_obj.fn = MagicMock()
        input_obj.fn.__name__ = "test_activity"
        input_obj.headers = {}
        input_obj.args = ()

        # Test attempt 5 - should not report
        mock_activity_info = MagicMock()
        mock_activity_info.attempt = 5

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
        ):
            with pytest.raises(Exception):
                await activity_interceptor.execute_activity(input_obj)

            mock_capture.assert_not_called()

        # Test attempt 6 - should report
        mock_activity_info.attempt = 6

        with (
            patch.object(activity, "info", return_value=mock_activity_info),
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope.return_value.__enter__.return_value = MagicMock()

            with pytest.raises(Exception):
                await activity_interceptor.execute_activity(input_obj)

            mock_capture.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_always_reports(self, mock_logger):
        """Test that workflows always report failures regardless of retry count."""
        mock_next = MagicMock(spec=WorkflowInboundInterceptor)
        mock_next.execute_workflow = AsyncMock(side_effect=Exception("Workflow error"))
        mock_next.init = MagicMock()

        interceptor = SentryInterceptor(mock_logger)
        input_obj = MagicMock(spec=WorkflowInterceptorClassInput)
        factory = interceptor.workflow_interceptor_class(input_obj)
        workflow_interceptor = factory(mock_next)

        workflow_input = MagicMock(spec=ExecuteWorkflowInput)
        workflow_input.type = MagicMock()
        workflow_input.type.__name__ = "TestWorkflow"
        workflow_input.headers = {}
        workflow_input.args = ()

        with (
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.capture_exception") as mock_capture,
            patch("zamp_public_workflow_sdk.temporal.interceptors.sentry_interceptor.push_scope") as mock_scope,
        ):
            mock_scope.return_value.__enter__.return_value = MagicMock()

            with pytest.raises(Exception):
                await workflow_interceptor.execute_workflow(workflow_input)

            # Workflows should always report (no retry count check)
            mock_capture.assert_called_once()

