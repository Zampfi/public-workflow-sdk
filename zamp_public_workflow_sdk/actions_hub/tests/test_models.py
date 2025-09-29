"""
Tests for models modules
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os
import inspect

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pantheon_v2.actions_hub.models.activity_models import Activity
from pantheon_v2.actions_hub.models.workflow_models import (
    Workflow,
    WorkflowParams,
    WorkflowCoordinates,
    PLATFORM_WORKFLOW_LABEL,
)
from pantheon_v2.actions_hub.models.business_logic_models import BusinessLogic
from pantheon_v2.actions_hub.models.decorators import external
from pantheon_v2.actions_hub.models.credentials_models import (
    ConnectionIdentifier,
    Connection,
    ActionConnectionsMapping,
)
from pantheon_v2.actions_hub.utils.context_utils import (
    get_variable_from_context,
    get_execution_mode_from_context,
)
from pantheon_v2.actions_hub.constants import ExecutionMode
from pantheon_v2.actions_hub.utils.datetime_utils import (
    convert_iso_to_timedelta,
)


class TestActivity:
    """Test the Activity model."""

    def test_activity_creation(self):
        """Test Activity creation."""
        mock_func = Mock()
        activity = Activity(
            name="test_activity", description="Test activity", func=mock_func
        )

        assert activity.name == "test_activity"
        assert activity.description == "Test activity"
        assert activity.func == mock_func
        assert activity._parameters is None
        assert activity._returns is None

    def test_activity_parameters_property(self):
        """Test Activity parameters property."""

        def test_func(param1: str, param2: int) -> bool:
            return True

        activity = Activity(
            name="test_activity", description="Test activity", func=test_func
        )

        parameters = activity.parameters
        assert parameters == (str, int)
        # Test caching
        assert activity._parameters == (str, int)

    def test_activity_returns_property(self):
        """Test Activity returns property."""

        def test_func() -> str:
            return "test"

        activity = Activity(
            name="test_activity", description="Test activity", func=test_func
        )

        returns = activity.returns
        assert returns is str
        # Test caching
        assert activity._returns is str

    def test_activity_parameters_with_self(self):
        """Test Activity parameters property filters out self parameter."""

        def test_func(self, param1: str) -> bool:
            return True

        activity = Activity(
            name="test_activity", description="Test activity", func=test_func
        )

        parameters = activity.parameters
        assert parameters == (str,)

    def test_activity_parameters_missing_annotation(self):
        """Test Activity parameters property raises error for missing annotation."""

        def test_func(param1, param2: int) -> bool:
            return True

        activity = Activity(
            name="test_activity", description="Test activity", func=test_func
        )

        with pytest.raises(ValueError, match="Parameter param1 has no type annotation"):
            activity.parameters

    def test_activity_returns_missing_annotation(self):
        """Test Activity returns property raises error for missing annotation."""

        def test_func():
            pass

        activity = Activity(
            name="test_activity", description="Test activity", func=test_func
        )

        with pytest.raises(ValueError, match="Return type is not specified"):
            activity.returns

    def test_activity_call(self):
        """Test Activity call method."""

        def test_func(x: int) -> int:
            return x * 2

        activity = Activity(
            name="test_activity", description="Test activity", func=test_func
        )

        result = activity(5)
        assert result == 10


class TestWorkflow:
    """Test the Workflow model."""

    def test_workflow_creation(self):
        """Test Workflow creation."""
        mock_func = Mock()
        workflow = Workflow(
            name="test_workflow",
            description="Test workflow",
            labels=["test"],
            class_type=type,
            func=mock_func,
        )

        assert workflow.name == "test_workflow"
        assert workflow.description == "Test workflow"
        assert workflow.labels == ["test"]
        assert workflow.class_type is type
        assert workflow.func == mock_func
        assert workflow._parameters is None
        assert workflow._returns is None

    def test_workflow_parameters_property(self):
        """Test Workflow parameters property."""

        def test_func(param1: str, param2: int) -> bool:
            return True

        workflow = Workflow(
            name="test_workflow",
            description="Test workflow",
            labels=["test"],
            class_type=type,
            func=test_func,
        )

        parameters = workflow.parameters
        assert parameters == (str, int)
        # Test caching
        assert workflow._parameters == (str, int)

    def test_workflow_returns_property(self):
        """Test Workflow returns property."""

        def test_func() -> str:
            return "test"

        workflow = Workflow(
            name="test_workflow",
            description="Test workflow",
            labels=["test"],
            class_type=type,
            func=test_func,
        )

        returns = workflow.returns
        assert returns is str
        # Test caching
        assert workflow._returns is str

    def test_workflow_parameters_with_self(self):
        """Test Workflow parameters property filters out self parameter."""

        def test_func(self, param1: str) -> bool:
            return True

        workflow = Workflow(
            name="test_workflow",
            description="Test workflow",
            labels=["test"],
            class_type=type,
            func=test_func,
        )

        parameters = workflow.parameters
        assert parameters == (str,)

    def test_workflow_parameters_missing_annotation(self):
        """Test Workflow parameters property raises error for missing annotation."""

        def test_func(param1, param2: int) -> bool:
            return True

        workflow = Workflow(
            name="test_workflow",
            description="Test workflow",
            labels=["test"],
            class_type=type,
            func=test_func,
        )

        with pytest.raises(ValueError, match="Parameter param1 has no type annotation"):
            workflow.parameters

    def test_workflow_returns_missing_annotation(self):
        """Test Workflow returns property with missing annotation."""

        def test_func():
            pass

        workflow = Workflow(
            name="test_workflow",
            description="Test workflow",
            labels=["test"],
            class_type=type,
            func=test_func,
        )

        # The updated implementation returns the annotation directly without validation
        assert workflow.returns == inspect.Signature.empty


class TestWorkflowModels:
    """Test other Workflow-related models."""

    def test_workflow_params(self):
        """Test WorkflowParams model."""
        params = WorkflowParams(
            workflow_name="test_workflow",
            result_type=str,
            args=(1, 2, 3),
            kwargs={"key": "value"},
        )

        assert params.workflow_name == "test_workflow"
        assert params.result_type is str
        assert params.args == (1, 2, 3)
        assert params.kwargs == {"key": "value"}

    def test_workflow_coordinates(self):
        """Test WorkflowCoordinates model."""
        coords = WorkflowCoordinates(
            workflow_name="test_workflow",
            absolute_file_path="/path/to/file.py",
            relative_file_path="file.py",
            line_number=42,
            module="test_module",
            class_name="TestClass",
        )

        assert coords.workflow_name == "test_workflow"
        assert coords.absolute_file_path == "/path/to/file.py"
        assert coords.relative_file_path == "file.py"
        assert coords.line_number == 42
        assert coords.module == "test_module"
        assert coords.class_name == "TestClass"

    def test_platform_workflow_label_constant(self):
        """Test PLATFORM_WORKFLOW_LABEL constant."""
        assert PLATFORM_WORKFLOW_LABEL == "platform"


class TestBusinessLogic:
    """Test the BusinessLogic model."""

    def test_business_logic_creation(self):
        """Test BusinessLogic creation."""
        mock_func = Mock()
        business_logic = BusinessLogic(
            name="test_business_logic",
            description="Test business logic",
            labels=["test"],
            func=mock_func,
        )

        assert business_logic.name == "test_business_logic"
        assert business_logic.description == "Test business logic"
        assert business_logic.labels == ["test"]
        assert business_logic.func == mock_func
        assert business_logic._parameters is None
        assert business_logic._returns is None

    def test_business_logic_parameters_property(self):
        """Test BusinessLogic parameters property."""

        def test_func(param1: str, param2: int) -> bool:
            return True

        business_logic = BusinessLogic(
            name="test_business_logic",
            description="Test business logic",
            labels=["test"],
            func=test_func,
        )

        parameters = business_logic.parameters
        assert parameters == (str, int)
        # Test caching
        assert business_logic._parameters == (str, int)

    def test_business_logic_returns_property(self):
        """Test BusinessLogic returns property."""

        def test_func() -> str:
            return "test"

        business_logic = BusinessLogic(
            name="test_business_logic",
            description="Test business logic",
            labels=["test"],
            func=test_func,
        )

        returns = business_logic.returns
        assert returns is str
        # Test caching
        assert business_logic._returns is str

    def test_business_logic_parameters_with_self(self):
        """Test BusinessLogic parameters property filters out self parameter."""

        def test_func(self, param1: str) -> bool:
            return True

        business_logic = BusinessLogic(
            name="test_business_logic",
            description="Test business logic",
            labels=["test"],
            func=test_func,
        )

        parameters = business_logic.parameters
        assert parameters == (str,)

    def test_business_logic_parameters_missing_annotation(self):
        """Test BusinessLogic parameters property raises error for missing annotation."""

        def test_func(param1, param2: int) -> bool:
            return True

        business_logic = BusinessLogic(
            name="test_business_logic",
            description="Test business logic",
            labels=["test"],
            func=test_func,
        )

        with pytest.raises(ValueError, match="Parameter param1 has no type annotation"):
            business_logic.parameters

    def test_business_logic_returns_missing_annotation(self):
        """Test BusinessLogic returns property raises error for missing annotation."""

        def test_func():
            pass

        business_logic = BusinessLogic(
            name="test_business_logic",
            description="Test business logic",
            labels=["test"],
            func=test_func,
        )

        with pytest.raises(ValueError, match="Return type is not specified"):
            business_logic.returns


class TestDecorators:
    """Test the decorators module."""

    def test_external_decorator(self):
        """Test the external decorator."""

        @external
        class TestClass:
            pass

        assert hasattr(TestClass, "_is_external")
        assert TestClass._is_external is True

    def test_external_decorator_function(self):
        """Test the external decorator on a function."""

        @external
        def test_function():
            pass

        assert hasattr(test_function, "_is_external")
        assert test_function._is_external is True


class TestCredentialsModels:
    """Test the credentials models."""

    def test_connection_identifier(self):
        """Test ConnectionIdentifier model."""
        conn_id = ConnectionIdentifier(
            connection_id="test_conn_123", organization_id="org_123", user_id="user_123"
        )

        assert conn_id.connection_id == "test_conn_123"
        assert conn_id.organization_id == "org_123"
        assert conn_id.user_id == "user_123"

    def test_connection(self):
        """Test Connection model."""
        conn = Connection(
            connection_id="test_conn_123", summary="Database connection for localhost"
        )

        assert conn.connection_id == "test_conn_123"
        assert conn.summary == "Database connection for localhost"

    def test_action_connections_mapping(self):
        """Test ActionConnectionsMapping model."""
        conn1 = Connection(connection_id="conn1", summary="Connection 1")
        conn2 = Connection(connection_id="conn2", summary="Connection 2")

        mapping = ActionConnectionsMapping(
            action_name="test_action", connections=[conn1, conn2]
        )

        assert mapping.action_name == "test_action"
        assert len(mapping.connections) == 2
        assert mapping.connections[0].connection_id == "conn1"
        assert mapping.connections[1].connection_id == "conn2"


class TestContextUtils:
    """Test the context utilities."""

    @patch(
        "pantheon_v2.actions_hub.utils.context_utils.structlog.contextvars.get_contextvars"
    )
    def test_get_variable_from_context(self, mock_get_contextvars):
        """Test get_variable_from_context function."""
        mock_context = {"test_var": "test_value", "other_var": 42}
        mock_get_contextvars.return_value = mock_context

        # Test with existing variable
        result = get_variable_from_context("test_var")
        assert result == "test_value"

        # Test with non-existing variable and default
        result = get_variable_from_context("non_existing", "default_value")
        assert result == "default_value"

        # Test with non-existing variable and no default
        result = get_variable_from_context("non_existing")
        assert result is None

    def test_get_execution_mode_from_context(self):
        """Test get_execution_mode_from_context function."""
        # Test default behavior (should return TEMPORAL as default)
        result = get_execution_mode_from_context()
        assert result == ExecutionMode.TEMPORAL


class TestDatetimeUtils:
    """Test the datetime utilities."""

    def test_convert_iso_to_timedelta(self):
        """Test convert_iso_to_timedelta function."""
        # Test with various ISO 8601 duration strings
        test_cases = [
            ("PT30S", 30),  # 30 seconds
            ("PT1M", 60),  # 1 minute
            ("PT1H", 3600),  # 1 hour
            ("P1D", 86400),  # 1 day
            ("PT1H30M", 5400),  # 1 hour 30 minutes
        ]

        for iso_string, expected_seconds in test_cases:
            result = convert_iso_to_timedelta(iso_string)
            assert result.total_seconds() == expected_seconds
