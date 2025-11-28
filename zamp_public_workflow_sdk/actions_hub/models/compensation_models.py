"""
Compensation models for ActionsHub saga pattern support.
"""

from pydantic import BaseModel, Field

from ..constants import CompensationActionType
from .decorators import external


@external
class CompensationConfig(BaseModel):
    """
    Configuration for compensation actions in the saga pattern.

    This model defines the compensation action that should be executed
    when a workflow needs to rollback due to a failure.
    """

    action_type: CompensationActionType = Field(description="Type of compensation action - ACTIVITY or WORKFLOW")
    action_name: str = Field(description="Name of the compensating activity or workflow")


def activity_compensation(action_name: str) -> CompensationConfig:
    """
    Helper to create an activity compensation config.

    Args:
        action_name: Name of the compensating activity

    Returns:
        CompensationConfig configured for activity compensation
    """
    return CompensationConfig(
        action_type=CompensationActionType.ACTIVITY,
        action_name=action_name,
    )


def workflow_compensation(action_name: str) -> CompensationConfig:
    """
    Helper to create a workflow compensation config.

    Args:
        action_name: Name of the compensating workflow

    Returns:
        CompensationConfig configured for workflow compensation
    """
    return CompensationConfig(
        action_type=CompensationActionType.WORKFLOW,
        action_name=action_name,
    )
