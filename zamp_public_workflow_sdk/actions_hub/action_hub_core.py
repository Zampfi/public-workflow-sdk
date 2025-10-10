"""
ActionsHub - Central Action Orchestrator

A central hub for registering and executing actions (activities, workflows, business logic)
independent of the Pantheon platform.
"""

import asyncio
import threading
from collections import defaultdict
from temporalio import workflow, activity
from zamp_public_workflow_sdk.temporal.interceptors.node_id_interceptor import (
    NODE_ID_HEADER_KEY,
)

from .models.mcp_models import MCPConfig
from .constants import DEFAULT_MODE, SKIP_SIMULATION_WORKFLOWS

with workflow.unsafe.imports_passed_through():
    from .constants import ExecutionMode
    from .utils.context_utils import (
        get_execution_mode_from_context,
        get_variable_from_context,
    )
    from pathlib import Path
    from functools import wraps
    from typing import Callable, Dict, List, Any, Union, Optional
    from datetime import timedelta

    from .models.workflow_models import (
        Workflow,
        WorkflowCoordinates,
        PLATFORM_WORKFLOW_LABEL,
    )

    from zamp_public_workflow_sdk.simulation.models import (
        ExecutionType,
        SimulationConfig,
        SimulationResponse,
    )

    from .models.business_logic_models import BusinessLogic
    from .models.core_models import (
        Action,
        ActionFilter,
        RetryPolicy,
        CodeExecutorConfig,
        ExecuteCodeParams,
    )
    from .constants import ActionType
    from .models.activity_models import Activity
    from .helper import (
        remove_connection_id,
        find_connection_id_path,
        inject_connection_id,
    )
    from zamp_public_workflow_sdk.temporal.data_converters.type_utils import get_fqn

    import structlog

    from .models.credentials_models import ActionConnectionsMapping
    from .models.decorators import external

    from zamp_public_workflow_sdk.temporal.interceptors.node_id_interceptor import (
        TEMPORAL_NODE_ID_KEY,
    )
    from zamp_public_workflow_sdk.simulation.workflow_simulation_service import (
        WorkflowSimulationService,
    )
    from .utils.datetime_utils import convert_iso_to_timedelta

    logger = structlog.get_logger(__name__)


@external
class ActionsHub:
    """Central hub for registering and executing actions (activities, workflows, business logic)"""

    """
    Activities
    """
    _activities: Dict[str, Activity] = {}
    _action_list: List[ActionConnectionsMapping] = []

    # Node ID tracking for unique identification of activities/workflows execution
    # Structure: {workflow_id: {action_name: count}}
    _node_id_tracker: Dict[str, Dict[str, int]] = {}

    # Thread lock for thread-safe access to _node_id_tracker
    _node_id_lock = threading.Lock()

    # Simulation
    _workflow_id_to_simulation_map: Dict[str, WorkflowSimulationService] = {}

    @classmethod
    def register_action_list(cls, action_list: List[ActionConnectionsMapping]):
        cls._action_list = [
            (
                ActionConnectionsMapping(**action)
                if not isinstance(action, ActionConnectionsMapping)
                else action
            )
            for action in action_list
        ]

    @classmethod
    def _get_action_name(cls, action: Union[str, Callable]) -> str:
        """
        Resolve the action name from various action types.

        Args:
            action: The action (activity/workflow) name or callable

        Returns:
            The resolved action name
        """
        if isinstance(action, str):
            return action

        # Handle bound methods (e.g., instance.method)
        if hasattr(action, "__self__"):
            return action.__self__.__class__.__name__

        # Handle unbound methods (e.g., Class.method)
        if hasattr(action, "__qualname__") and "." in action.__qualname__:
            # For qualified names like "ClassName.method", use the class name
            return action.__qualname__.split(".")[0]

        return action.__name__

    @classmethod
    def _generate_node_id_for_action(
        cls, action: Union[str, Callable]
    ) -> tuple[str, str, str]:
        """
        Generate node_id for an action (activity or workflow) execution.

        Args:
            action: The action (activity/workflow) name or callable

        Returns:
            Tuple of (action_name, workflow_id, node_id)
        """
        action_name = cls._get_action_name(action)
        workflow_id = cls._get_current_workflow_id()
        node_id = cls._get_node_id(workflow_id=workflow_id, action_name=action_name)
        return action_name, workflow_id, node_id

    @classmethod
    def _get_node_id(cls, workflow_id: str, action_name: str) -> str:
        """
        Generate a unique node_id for an action execution.

        For actions within child workflows, the node_id will be hierarchical:
        - Main workflow activity: Activity#1 (or Activity#2 if called again)
        - Child workflow: ChildWorkflow#1
        - Activity within child workflow: ChildWorkflow#1.Activity#1
        - Child workflow within child workflow: ChildWorkflow#1.NestedChildWorkflow#1

        Args:
            workflow_id: The workflow ID
            action_name: The name of the action (activity/workflow)

        Returns:
            A unique node_id in hierarchical format
        """
        with cls._node_id_lock:
            if workflow_id not in cls._node_id_tracker:
                cls._node_id_tracker[workflow_id] = defaultdict(int)

            info = workflow.info()
            if info.headers and NODE_ID_HEADER_KEY in info.headers:
                node_id_payload = info.headers[NODE_ID_HEADER_KEY]
                parent_node_id = workflow.payload_converter().from_payload(
                    node_id_payload, str
                )
                if parent_node_id:
                    tracking_key = f"{parent_node_id}.{action_name}"
                else:
                    tracking_key = action_name
            else:
                tracking_key = action_name

            cls._node_id_tracker[workflow_id][tracking_key] += 1
            count = cls._node_id_tracker[workflow_id][tracking_key]

            node_id = f"{tracking_key}#{count}"

        return node_id

    @classmethod
    def _get_simulation_response(
        cls,
        workflow_id: str,
        node_id: str,
        action: Union[str, Callable] = None,
        return_type: type | None = None,
    ) -> SimulationResponse:
        """Get simulation response for a workflow execution and handle return type conversion."""

        action_name = cls._get_action_name(action)
        if action_name and action_name in SKIP_SIMULATION_WORKFLOWS:
            return SimulationResponse(
                execution_type=ExecutionType.EXECUTE, execution_response=None
            )

        simulation = cls.get_simulation_from_workflow_id(workflow_id)
        if not simulation:
            return SimulationResponse(
                execution_type=ExecutionType.EXECUTE, execution_response=None
            )

        simulation_response = simulation.get_simulation_response(node_id)
        if simulation_response.execution_type == ExecutionType.MOCK:
            if return_type is None and action:
                return_type = cls._get_action_return_type(action)

            simulation_response.execution_response = cls._convert_result_to_model(
                result=simulation_response.execution_response, return_type=return_type
            )

        return simulation_response

    @classmethod
    def _get_action_return_type(cls, action_name: str | Callable) -> type | None:
        """Get the return type from action using unified Action interface."""
        if isinstance(action_name, str):
            name = action_name
        else:
            name = action_name.__name__
        actions = cls.get_available_actions(ActionFilter(name=name))
        if actions:
            return actions[0].returns

        return None

    @classmethod
    def _convert_result_to_model(cls, result: Any, return_type: type | None) -> Any:
        """Convert result to Pydantic model if return_type is specified and result is a dict."""
        if not return_type or result is None:
            return result

        if hasattr(return_type, "model_validate") and isinstance(result, dict):
            try:
                return return_type.model_validate(result)
            except Exception as e:
                logger.warning(
                    "Failed to convert simulation result to Pydantic model %s: %s",
                    return_type.__name__,
                    e,
                )
                return result

        return result

    @classmethod
    async def init_simulation_for_workflow(
        cls, simulation_config: SimulationConfig, workflow_id: str
    ) -> None:
        """
        Initialize simulation for a workflow.

        Args:
            simulation_config: Simulation configuration
            workflow_id: Workflow ID to associate with simulation
        """
        simulation_service = WorkflowSimulationService(simulation_config)
        cls._workflow_id_to_simulation_map[workflow_id] = simulation_service
        await simulation_service._initialize_simulation_data()
        logger.info("Simulation initialized for workflow", workflow_id=workflow_id)

    @classmethod
    def get_simulation_from_workflow_id(
        cls, workflow_id: str
    ) -> WorkflowSimulationService:
        return cls._workflow_id_to_simulation_map.get(workflow_id)

    @classmethod
    def _get_current_workflow_id(cls) -> str:
        """
        Get current workflow ID.
        This should be called from within a workflow execution.

        Returns:
            The workflow_id
        """
        execution_mode: ExecutionMode = get_execution_mode_from_context()
        if execution_mode == ExecutionMode.API:
            request_id = get_variable_from_context("request_id", "unknown")
            logger.info(
                "workflow not available for API mode, using request_id as workflow_id",
                request_id=request_id,
            )
            return request_id
        try:
            workflow_info = workflow.info()
            return workflow_info.workflow_id
        except Exception:
            logger.error("workflow info not available, using fallback workflow_id")
            return DEFAULT_MODE

    @classmethod
    def get_node_id_tracker_state(cls) -> Dict[str, Dict[str, int]]:
        """
        Get the current state of the node_id tracker for debugging and testing.

        Returns:
            The current node_id_tracker dictionary
        """
        with cls._node_id_lock:
            return {
                workflow_id: dict(action_counts)
                for workflow_id, action_counts in cls._node_id_tracker.items()
            }

    @classmethod
    def clear_node_id_tracker(cls):
        """
        Clear the node_id tracker. Useful for testing.
        """
        with cls._node_id_lock:
            cls._node_id_tracker.clear()

    @classmethod
    def register_activity(
        cls,
        description: str,
        labels: Optional[List[str]] = None,
        mcp_config: Optional[MCPConfig] = None,
    ):
        """
        Register an activity decorator with optional description, labels, and MCP access control

        Args:
            description: Human-readable description of the activity
            mcp_config: Optional MCPConfig DTO with service_name and accesses list
        """

        def decorator(func: Callable) -> Callable:
            activity_name = func.__name__
            if activity_name in cls._activities:
                raise ValueError(
                    f"Activity '{activity_name}' already registered. Please use a unique name."
                )

            # Check if the function is async
            is_async = asyncio.iscoroutinefunction(func)

            # Create the appropriate wrapper
            if is_async:

                @activity.defn(name=activity_name)
                @wraps(func)
                async def wrapper(*args, **kwargs):
                    return await func(*args, **kwargs)

            else:

                @activity.defn(name=activity_name)
                @wraps(func)
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)

            # Create activity and set metadata
            new_activity = Activity(
                name=func.__name__,
                description=description,
                func=wrapper,
                mcp_config=mcp_config,
            )

            assert new_activity.parameters is not None
            assert new_activity.returns is not None

            cls._activities[func.__name__] = new_activity
            wrapper._is_activity = True
            wrapper._description = description
            return wrapper

        return decorator

    @classmethod
    def get_activity_details(cls, activity_name: str) -> Activity:
        return cls._activities[activity_name]

    @classmethod
    def get_activity_by_name(cls, name: str) -> Optional[Activity]:
        """
        Get activity by name for internal use.
        Args:
            name: Name of the activity to retrieve
        Returns:
            Activity object if found, None otherwise
        """
        return cls._activities.get(name)

    @classmethod
    def get_available_activities(cls) -> list[Activity]:
        return list(cls._activities.values())

    @classmethod
    async def execute_activity(
        cls,
        activity: str | Callable,
        *args,
        execution_mode: ExecutionMode | None = None,
        return_type: type | None = None,
        start_to_close_timeout: timedelta = timedelta(minutes=10),
        retry_policy: RetryPolicy = RetryPolicy.default(),
        task_queue: str | None = None,
        **kwargs,
    ):
        # Check if execution_mode is set to "API" in context variables
        if execution_mode is None:
            execution_mode = get_execution_mode_from_context()
            
        if execution_mode == ExecutionMode.API:
            # Direct function execution mode - bypass Temporal
            logger.info(
                "Executing activity in API mode, bypassing Temporal",
                activity_name=cls._get_action_name(activity),
            )

            # Get the activity function
            if isinstance(activity, str):
                if activity not in cls._activities:
                    raise ValueError(f"Activity '{activity}' not found")
                activity_obj = cls._activities[activity]
                func = activity_obj.func
            else:
                func = activity

            # Execute the function directly
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            else:
                return func(*args)

        # Generate node_id for this activity execution
        activity_name, workflow_id, node_id = cls._generate_node_id_for_action(activity)

        # Check for simulation result
        simulation_result = cls._get_simulation_response(
            workflow_id=workflow_id,
            node_id=node_id,
            action=activity,
            return_type=return_type,
        )
        if simulation_result.execution_type == ExecutionType.MOCK:
            logger.info(
                "Activity mocked",
                node_id=node_id,
            )
            return simulation_result.execution_response
        
        # Temporal execution mode
        # Convert ISO string to timedelta
        retry_policy.initial_interval = convert_iso_to_timedelta(
            retry_policy.initial_interval
        )
        retry_policy.maximum_interval = convert_iso_to_timedelta(
            retry_policy.maximum_interval
        )

        node_id_arg = {TEMPORAL_NODE_ID_KEY: node_id}
        args = (node_id_arg,) + args

        # Executing in temporal mode
        logger.info(
            "Executing activity",
            activity_name=activity_name,
            node_id=node_id,
            workflow_id=workflow_id,
        )

        return await workflow.execute_activity(
            activity,
            args=args,
            result_type=return_type,
            start_to_close_timeout=start_to_close_timeout,
            retry_policy=retry_policy.to_temporal_retry_policy(),
            task_queue=task_queue,
            **kwargs,
        )

    """
    Workflows
    """
    _workflows: Dict[str, Workflow] = {}

    @classmethod
    def register_workflow_defn(cls, description: str, labels: list[str]):
        def decorator(target: type):
            setattr(target, "_is_workflow_defn", True)
            workflow_name = target.__name__
            new_workflow = Workflow(
                name=workflow_name,
                description=description,
                labels=labels,
                class_type=target,
            )

            if workflow_name in cls._workflows:
                new_workflow.func = cls._workflows[workflow_name].func

            cls._workflows[workflow_name] = new_workflow
            return workflow.defn(target, name=target.__name__)

        return decorator

    @classmethod
    def register_workflow_run(cls, func: Callable) -> Callable:
        @workflow.run
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        workflow_name = func.__name__
        if hasattr(func, "__qualname__"):
            workflow_name = func.__qualname__.split(".")[0]

        if workflow_name not in cls._workflows:
            cls._workflows[workflow_name] = Workflow(
                name=workflow_name,
                description="",
                labels=[],
                class_type=type(func),
            )

        cls._workflows[workflow_name].func = func
        return wrapper

    @classmethod
    def register_workflow_signal(cls, name: str = None):
        def decorator(func: Callable) -> Callable:
            @workflow.signal(name=name)
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    @classmethod
    def register_workflow_query(cls, name: str = None):
        """Register a workflow query method.
        Args:
            name (str, optional): Name for the query. Defaults to function name if None.
        Returns:
            Callable: Decorator that registers the function as a workflow query.
        """

        def decorator(func: Callable) -> Callable:
            @workflow.query(name=name)
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    @classmethod
    def get_workflow(cls, workflow_name: str) -> Workflow:
        return cls._workflows[workflow_name]

    @classmethod
    def get_available_workflows(cls, labels: list[str]) -> list[Workflow]:
        workflows = []
        if len(labels) == 0:
            return list(cls._workflows.values())

        for _workflow in cls._workflows.values():
            if PLATFORM_WORKFLOW_LABEL in _workflow.labels or any(
                label in _workflow.labels for label in labels
            ):
                workflows.append(_workflow)

        return workflows

    @classmethod
    def get_all_workflows(cls) -> list[str]:
        return list(cls._workflows.keys())

    @classmethod
    def get_workflow_coordinates(cls, workflow_name: str) -> WorkflowCoordinates:
        """
        Get the coordinates for a workflow.

        Args:
            workflow_name (str): Name of the workflow to get coordinates for

        Returns:
            WorkflowCoordinates: Workflow coordinates

        Raises:
            ValueError: If workflow is not found or workflow function is not available
        """
        if workflow_name not in cls._workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")

        workflow = cls._workflows[workflow_name]
        func = workflow.func

        if func is None:
            raise ValueError(f"Workflow '{workflow_name}' function is not available")

        # Get the source file path and line number
        absolute_file_path = func.__code__.co_filename
        relative_file_path = str(Path(absolute_file_path).relative_to(Path.cwd()))
        line_number = func.__code__.co_firstlineno
        module = func.__module__

        # Get class name if it's a method
        class_name = None
        if hasattr(func, "__qualname__"):
            qualname_parts = func.__qualname__.split(".")
            if len(qualname_parts) > 1:
                class_name = qualname_parts[0]

        return WorkflowCoordinates(
            workflow_name=workflow_name,
            absolute_file_path=absolute_file_path,
            relative_file_path=relative_file_path,
            line_number=line_number,
            module=module,
            class_name=class_name,
        )

    @classmethod
    async def execute_child_workflow(
        cls,
        workflow_name: Union[str, Callable],
        *args,
        result_type: type | None = None,
        **kwargs,
    ):
        execution_mode = get_execution_mode_from_context()
        if execution_mode == ExecutionMode.API:
            # Direct function execution mode - bypass Temporal
            logger.info(
                "Executing child workflow in API mode, bypassing Temporal",
                workflow_name=cls._get_action_name(workflow_name),
            )

            # Get the workflow function
            if isinstance(workflow_name, str):
                if workflow_name not in cls._workflows:
                    raise ValueError(f"Workflow '{workflow_name}' not found")
                workflow_obj = cls._workflows[workflow_name]
                if not workflow_obj.func:
                    raise ValueError(
                        f"Workflow function not available for {workflow_name}"
                    )
                return await workflow_obj.func(workflow_obj.class_type(), *args)
            else:
                func = workflow_name

            if func is None:
                raise ValueError(f"Workflow function not available for {workflow_name}")

            # Execute the function directly
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            else:
                return func(*args)

        # Generate node_id for this child workflow execution
        child_workflow_name, workflow_id, node_id = cls._generate_node_id_for_action(
            workflow_name
        )

        # Check for simulation result
        simulation_result = cls._get_simulation_response(
            workflow_id=workflow_id,
            node_id=node_id,
            action=workflow_name,
            return_type=result_type,
        )

        if simulation_result.execution_type == ExecutionType.MOCK:
            logger.info(
                "Child workflow mocked",
                node_id=node_id,
            )
            return simulation_result.execution_response
        
        # Temporal execution mode
        node_id_arg = {TEMPORAL_NODE_ID_KEY: node_id}
        args = (node_id_arg,) + args

        # Executing in temporal mode
        logger.info(
            "Executing child workflow",
            workflow_name=child_workflow_name,
            node_id=node_id,
            workflow_id=workflow_id,
        )

        return await workflow.execute_child_workflow(
            workflow_name,
            result_type=result_type,
            args=args,
            **kwargs,
        )

    @classmethod
    async def start_child_workflow(
        cls,
        workflow_name: Union[str, Callable],
        *args,
        result_type: type | None = None,
        **kwargs,
    ):
        # Generate node_id for this child workflow execution
        child_workflow_name, workflow_id, node_id = cls._generate_node_id_for_action(
            workflow_name
        )

        # Check for simulation result
        simulation_result = cls._get_simulation_response(
            workflow_id=workflow_id,
            node_id=node_id,
            action=workflow_name,
            return_type=result_type,
        )
        if simulation_result.execution_type == ExecutionType.MOCK:
            logger.info(
                "Child workflow mocked",
                activity_name=workflow_name,
                node_id=node_id,
            )
            return simulation_result.execution_response

        logger.info(
            "Starting child workflow",
            workflow_name=child_workflow_name,
            node_id=node_id,
            workflow_id=workflow_id,
        )

        node_id_arg = {TEMPORAL_NODE_ID_KEY: node_id}
        args = (node_id_arg,) + args

        return await workflow.start_child_workflow(
            workflow_name,
            result_type=result_type,
            args=args,
            **kwargs,
        )

    @classmethod
    async def workflow_sleep(cls, seconds: int, summary: str = ""):
        return await workflow.sleep(seconds, summary=summary)

    """
    Business Logic
    """
    _business_logic_methods: Dict[str, BusinessLogic] = {}

    @classmethod
    def register_business_logic(cls, description: str, labels: list[str]) -> Callable:
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            cls._business_logic_methods[func.__name__] = BusinessLogic(
                name=func.__name__,
                description=description,
                labels=labels,
                func=wrapper,
            )
            return wrapper

        return decorator

    @classmethod
    def get_available_business_logic_list(cls) -> list[BusinessLogic]:
        return list(cls._business_logic_methods.values())

    @classmethod
    def get_business_logic_by_labels(cls, labels: list[str]) -> list[BusinessLogic]:
        return [
            business_logic
            for business_logic in cls._business_logic_methods.values()
            if any(label in business_logic.labels for label in labels)
        ]

    """
    Common Methods
    """

    @classmethod
    def get_available_actions(cls, filters: ActionFilter) -> list[Action]:
        actions = []
        workflow_list = cls.get_available_workflows(filters.labels)
        for wf in workflow_list:
            actions.append(Action.from_workflow(wf))

        activity_list = cls.get_available_activities()
        for act in activity_list:
            actions.append(Action.from_activity(act))

        for business_logic in cls.get_available_business_logic_list():
            actions.append(Action.from_business_logic(business_logic))

        return filters.filter_actions(actions)

    @classmethod
    def get_action_schemas(cls) -> List[Dict[str, Any]]:
        """
        Process action schemas to handle credential selection appropriately.

        Logic:
        - If 0 or 1 connections: Remove connection_id from input schema
        - If multiple connections: Include connections list for LLM selection
        """

        schemas = []

        for action in cls._action_list:
            actions = cls.get_available_actions(ActionFilter(name=action.action_name))
            if len(actions) == 0:
                raise ValueError(f"Action {action.action_name} not found")

            action_obj = actions[0]
            schema = cls._get_base_schema(action_obj)

            if len(action.connections) == 0:
                schema["args"] = remove_connection_id(schema["args"])
            elif len(action.connections) == 1:
                # schema["_connection_path"] = find_connection_id_path(schema["args"])
                schema["args"] = remove_connection_id(schema["args"])
            else:
                schema["connections"] = [
                    conn.model_dump() for conn in action.connections
                ]

            schemas.append(schema)

        return schemas

    @classmethod
    def _get_base_schema(cls, action: Action) -> Dict[str, Any]:
        """
        Get the base schema for an action from its registered action.

        Args:
            action: Action to get schema for

        Returns:
            Dictionary containing the action's schema
        """

        action_schema = action.get_model_schema()
        return action_schema

    @classmethod
    async def execute_action(
        cls,
        action_name: str,
        params: Dict[str, Any],
        summary: Optional[str] = None,
        activity_retry_policy: RetryPolicy = RetryPolicy.default(),
    ) -> Any:
        actions = cls.get_available_actions(ActionFilter(name=action_name))
        if len(actions) == 0:
            raise ValueError(f"Action {action_name} not found")

        action = actions[0]
        # Find the matching action mapping in the list
        action_mapping = next(
            (
                mapping
                for mapping in cls._action_list
                if mapping.action_name == action_name
            ),
            None,
        )
        connections = action_mapping.connections if action_mapping else []

        if len(connections) == 0:
            return await cls._dispatch_action(
                action,
                activity_retry_policy,
                params,
                summary=summary,
            )
        elif len(connections) == 1:
            connection_id = connections[0].connection_id
            schema = cls._get_base_schema(action)
            path = find_connection_id_path(schema["args"])

            enriched_params_list = inject_connection_id(params, connection_id, path)
            # Unpack the list as separate arguments
            return await cls._dispatch_action(
                action,
                activity_retry_policy,
                *enriched_params_list,
                summary=summary,
            )
        else:
            return await cls._dispatch_action(
                action,
                activity_retry_policy,
                params,
                summary=summary,
            )

    @classmethod
    async def _dispatch_action(
        cls, action: Action, activity_retry_policy: RetryPolicy, *args, **kwargs
    ) -> Any:
        """Dispatch the action to its registered activity"""

        if action.action_type == ActionType.ACTIVITY:
            return await cls.execute_activity(
                action.name,
                retry_policy=activity_retry_policy,
                *args,
                return_type=action.returns,
                **kwargs,
            )
        elif action.action_type == ActionType.WORKFLOW:
            return await cls.execute_child_workflow(
                action.name,
                *args,
                result_type=action.returns,
                **kwargs,
            )
        # TODO: Remove support for business logic as it's going to be deprecated
        elif action.action_type == ActionType.BUSINESS_LOGIC:
            return await cls.execute_activity(
                "execute_code",
                CodeExecutorConfig(
                    timeout_seconds=30,
                ),
                ExecuteCodeParams(
                    function=get_fqn(action.func),
                    args=args,
                    kwargs=kwargs,
                ),
            )
        else:
            raise ValueError(f"Unknown action type: {action.action_type}")
