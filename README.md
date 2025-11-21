# Development Setup Guide

This guide will help you set up your development environment for the `zamp-public-workflow-sdk` module.

## Prerequisites

- Python 3.12.x
- `git` installed on your system
- `uv` package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

## Setup Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd public-workflow-sdk
```

### 2. Install Dependencies

Install both runtime and development dependencies using `uv`:

```bash
uv sync --all-groups
```

This command will:
- Create a virtual environment automatically
- Install all project dependencies from `pyproject.toml`
- Install development dependencies from the `[dependency-groups]` section

### 3. Initialize Pre-commit Hooks

Set up pre-commit hooks to automatically format and lint your code:

```bash
uv run pre-commit install
```

To manually run pre-commit on all files:

```bash
uv run pre-commit run --all-files
```

## Running Tests

Run the test suite :

```bash
bash scripts/tests.sh

```

## Development Workflow


### Type Checking

Run type checking with mypy:

```bash
uv run mypy zamp_public_workflow_sdk/
```

### Linting

Run linting with ruff:

```bash
uv run ruff check zamp_public_workflow_sdk/
```

## Project Structure

```
public-workflow-sdk/
├── zamp_public_workflow_sdk/  # Main package
│   ├── actions_hub/            # Actions Hub functionality
│   ├── simulation/             # Workflow simulation
│   └── temporal/               # Temporal workflow integration
├── tests/                      # Test files
├── sample/                     # Sample implementations
└── pyproject.toml             # Project configuration (dependencies, build settings, tool configs)
```

## Building and Publishing

To build and publish the package:

```bash
# Build the package
uv build

# The built distribution files will be in the dist/ directory
# Publishing is handled through CI/CD pipelines
```

## Troubleshooting

### Dependency Issues

If you encounter issues with dependencies:

```bash
# Remove the virtual environment and lock file
rm -rf .venv uv.lock

# Reinstall dependencies
uv sync --all-groups
```

### Python Version

If you need to install Python 3.12.x, use:
- **macOS**: `brew install python@3.12`
- **Linux**: Use your package manager or pyenv
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

Alternatively, you can use `uv` to manage Python versions:

```bash
# Install a specific Python version
uv python install 3.12

# Use a specific Python version for the project
uv python pin 3.12
```


## Contributing

1. Create a new branch for your feature/bugfix
2. Make your changes
3. Ensure all tests pass: `bash scripts/tests.sh`
4. Ensure pre-commit checks pass: `uv run pre-commit run --all-files`
5. Commit your changes (pre-commit hooks will run automatically)
6. Push and create a pull request
