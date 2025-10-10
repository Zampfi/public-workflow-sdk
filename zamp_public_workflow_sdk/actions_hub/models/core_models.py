"""
Models for ActionsHub - independent of Pantheon platform.
"""

from pydantic import BaseModel, Field
from typing import Any, Callable, Optional, Dict
from datetime import timedelta
from .activity_models import Activity
from .workflow_models import Workflow
from .business_logic_models import BusinessLogic
from .mcp_models import MCPConfig
from ..constants import ActionType
from temporalio.common import RetryPolicy as TemporalRetryPolicy
from .decorators import external


class Action(BaseModel):
    name: str
    description: str
    args: tuple
    returns: Any
    long_description: str | None = None
    action_type: ActionType
    labels: list[str] = []
    func: Callable | None = None
    mcp_config: Optional[MCPConfig] = None

    @classmethod
    def from_workflow(cls, workflow: Workflow) -> "Action":
        return cls(
            name=workflow.name,
            description=workflow.description,
            args=workflow.parameters,
            returns=workflow.returns,
            long_description=workflow.func.__doc__,
            action_type=ActionType.WORKFLOW,
        )

    @classmethod
    def from_activity(cls, activity: Activity) -> "Action":
        return cls(
            name=activity.name,
            description=activity.description,
            args=activity.parameters,
            returns=activity.returns,
            long_description=activity.func.__doc__,
            action_type=ActionType.ACTIVITY,
            labels=activity.labels,
            mcp_config=activity.mcp_config,
        )

    @classmethod
    def from_business_logic(cls, business_logic: BusinessLogic) -> "Action":
        return cls(
            name=business_logic.name,
            description=business_logic.description,
            args=business_logic.parameters,
            returns=business_logic.returns,
            long_description=business_logic.func.__doc__,
            action_type=ActionType.BUSINESS_LOGIC,
            func=business_logic.func,
        )

    def get_model_schema(self):
        """
        Returns something like this:
        {
            "name": "extract_text_from_image",
            "args": [
                {
                    "content": {
                        "type": "BytesIO",
                        "description": "A BytesIO object"
                    }
                },
                {
                    "id": {
                        "type": "str",
                        "description": "The id of the object"
                    },
                    "number": {
                        "type": "int",
                        "description": "The number of the object"
                    }
                }
            ],
            "returns": {
                "extracted_text": {
                    "type": "str",
                    "description": "The extracted text from the object"
                }
            }
        }
        """
        from ..utils.serializer import Serializer

        result = {
            "name": self.name,
            "args": [Serializer.get_schema_from_class(arg) for arg in self.args],
            "returns": Serializer.get_schema_from_class(self.returns),
            "description": self.description,
            "long_description": self.long_description,
        }

        return result


class ActionFilter(BaseModel):
    name: Optional[str] = Field(
        default="", description="The name of the action to filter by"
    )
    labels: Optional[list[str]] = Field(
        default=[], description="The labels of the action to filter by"
    )
    resticted_action_set: Optional[list[str]] = Field(
        default=[], description="The action set to filter by"
    )

    def filter_actions(self, actions: list[Action]) -> list[Action]:
        filtered_actions = []
        for action in actions:
            if (
                self.resticted_action_set is not None
                and len(self.resticted_action_set) > 0
                and action.name in self.resticted_action_set
            ):
                filtered_actions.append(action)
                continue

            if self.name is not None and self.name != "" and action.name == self.name:
                filtered_actions.append(action)
                continue

        return filtered_actions


@external
class RetryPolicy(BaseModel):
    initial_interval: timedelta
    maximum_attempts: int
    maximum_interval: timedelta
    backoff_coefficient: float

    def to_temporal_retry_policy(self) -> TemporalRetryPolicy:
        return TemporalRetryPolicy(
            initial_interval=self.initial_interval,
            maximum_attempts=self.maximum_attempts,
            maximum_interval=self.maximum_interval,
            backoff_coefficient=self.backoff_coefficient,
        )

    # Define a static property for the default retry policy
    @staticmethod
    def default() -> "RetryPolicy":
        # ~11 retries approximating around 1 hour
        return RetryPolicy(
            initial_interval=timedelta(seconds=30),
            maximum_attempts=11,  # 10 retries + 1 initial attempt
            maximum_interval=timedelta(minutes=15),
            backoff_coefficient=1.5,
        )

    @staticmethod
    def child_workflow_default() -> "RetryPolicy":
        return RetryPolicy(
            initial_interval=timedelta(seconds=5),
            maximum_attempts=3,  # 2 retries + 1 initial attempt
            maximum_interval=timedelta(minutes=1),
            backoff_coefficient=1.5,
        )


@external
class CodeExecutorConfig(BaseModel):
    timeout_seconds: int = Field(
        default=30,
        description="Maximum execution time allowed for functions in seconds",
    )


class ExecuteCodeParams(BaseModel):
    function: Any = Field(..., description="Callable function to execute")
    args: tuple = Field(
        default=(), description="Positional arguments to pass to the function"
    )
    kwargs: Dict[str, Any] = Field(
        default_factory=dict, description="Keyword arguments to pass to the function"
    )
