"""
Constants for ActionsHub - independent of Pantheon platform.
"""

from enum import Enum

# Formatting constants
SEPARATOR_LINE = "-" * 80

# Prompt structure constants
ACTION_HEADER_TEMPLATE = "## Action: {}"
NUMBERED_ACTION_HEADER_TEMPLATE = "## Action {}: {}"
DESCRIPTION_TEMPLATE = "**Description**: {}"
DETAILED_DESCRIPTION_TEMPLATE = "**Detailed description**: {}"
INPUT_PARAMETERS_HEADER = "### Input Parameters:"
RETURN_VALUES_HEADER = "### Return Values:"
NO_INPUT_PARAMETERS_MESSAGE = "  No input parameters required."
NO_RETURN_VALUES_MESSAGE = "  No return values."
DEFAULT_MODE = "default"

# Error messages
ERROR_ACTIONS_NOT_FOUND = "Some actions listed in action_names are not found"


class ActionType(Enum):
    """Action types for ActionsHub."""

    ACTIVITY = 0
    WORKFLOW = 1
    BUSINESS_LOGIC = 2


class ExecutionMode(str, Enum):
    """
    Execution mode for the action hub activity and workflows
    API: for API execution mode, which directly calls the function
    TEMPORAL: for Temporal execution mode, which calls the function using Temporal constructs
    """

    API = "API"
    TEMPORAL = "TEMPORAL"


# Simulation constants
SKIP_SIMULATION_WORKFLOWS = [
    "SimulationWorkflow",
    "FetchTemporalWorkflowHistoryWorkflow",
]
