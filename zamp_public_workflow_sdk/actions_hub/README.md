# ActionsHub - Central Action Orchestrator

The ActionsHub is the central orchestrator for registering and executing all activities, workflows, and business logic. It provides a unified interface for action discovery and execution, independent of the Pantheon platform.

## 🎯 Purpose

The ActionsHub serves as the central registry and execution engine for:
- **Activities**: Individual units of work that can be executed
- **Workflows**: Complex multi-step processes with state management
- **Business Logic**: Custom business rules and processing functions
- **Action Discovery**: Runtime discovery of available actions and their schemas

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Executing Activities

```python
from zamp_public_workflow_sdk.actions_hub import ActionsHub
from zamp_public_workflow_sdk.actions_hub.models.core_models import RetryPolicy
from datetime import datetime, timedelta

# Execute a simple activity
result = await ActionsHub.execute_activity(
    activity_function,
    input_data,
    return_type=ExpectedOutputType,
    start_to_close_timeout=timedelta(seconds=30)
)

# Execute activity with retry policy
result = await ActionsHub.execute_activity(
    activity_function,
    input_data,
    return_type=ExpectedOutputType,
    retry_policy=RetryPolicy(
        initial_interval=timedelta(seconds=1),
        maximum_interval=timedelta(seconds=60),
        maximum_attempts=3
    )
)
```

### Executing Workflows

```python
# Execute child workflow
workflow_result = await ActionsHub.execute_child_workflow(
    WorkflowClass,
    workflow_input,
    return_type=WorkflowOutputType
)

# Start child workflow (fire and forget)
workflow_handle = await ActionsHub.start_child_workflow(
    WorkflowClass,
    workflow_input
)
```

## 📋 API Surface

### Core Methods

- **execute_activity()** - Execute an activity with input data and return typed results
- **execute_child_workflow()** - Execute a child workflow and wait for completion
- **start_child_workflow()** - Start a child workflow without waiting for completion
- **register_activity()** - Register a new activity with the hub
- **register_workflow_defn()** - Register a new workflow definition
- **register_business_logic()** - Register business logic functions
- **get_available_actions()** - Get all available actions with filtering
- **get_action_schemas()** - Get action schemas for LLM consumption

## 🏗️ Architecture

### Independent Components

This ActionsHub implementation is completely independent of the Pantheon platform and includes:

- **Core Models**: Action, Workflow, Activity, BusinessLogic
- **Execution Engine**: Temporal.io integration for workflows and activities
- **Context Management**: Simplified context utilities without circular dependencies
- **Schema Generation**: Automatic schema generation for LLM consumption
- **Retry Policies**: Configurable retry policies for robust execution

### Dependencies

- `temporalio` - Temporal workflow engine
- `zamp-public-workflow-sdk` - Custom SDK for node ID tracking
- `structlog` - Structured logging
- `pydantic` - Data validation and serialization
- `pandas` - Data processing utilities

## 🔧 Migration from Pantheon

This ActionsHub is designed to be a drop-in replacement for the Pantheon ActionsHub with minimal changes:

1. **Import Changes**: Update import paths from `pantheon_v2.platform.orchestrator.actions` to `actions_hub`
2. **Model Imports**: Use `actions_hub.models.core_models` for core models and `actions_hub.models.utils_models` for utility models
3. **No Functional Changes**: All method signatures and behavior remain identical
4. **Simplified Dependencies**: Removed complex platform-specific dependencies

## 📁 Structure

```
actions_hub/
├── __init__.py                 # Main exports
├── action_hub_core.py         # Core ActionsHub class
├── constants.py               # Constants and enums (includes ActionType)
├── helper.py                  # Helper functions
├── requirements.txt           # Dependencies
├── README.md                  # This file
├── models/                    # Model definitions
│   ├── __init__.py
│   ├── core_models.py         # Core data models (Action, RetryPolicy, etc.)
│   ├── utils_models.py        # Utility models (ActionSchema, etc.)
│   ├── decorators.py
│   ├── credentials_models.py
│   ├── workflow_models.py
│   ├── business_logic_models.py
│   └── activity_models.py
├── utils/                     # Utility functions
│   ├── __init__.py
│   ├── utils.py
│   ├── context_utils.py       # Context utilities
│   └── datetime_utils.py      # Datetime utilities
└── tests/                     # Test files
```

## 🧪 Testing

```bash
# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=actions_hub
```

## 📝 License

This project is part of the Zamp platform and follows the same licensing terms.
