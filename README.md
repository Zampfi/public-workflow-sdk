# Development Setup Guide

This guide will help you set up your development environment for the `zamp-public-workflow-sdk` module.

## Prerequisites

- Python 3.12.x
- `git` installed on your system

## Setup Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd public-workflow-sdk
```

### 2. Create a Virtual Environment

Create a virtual environment using Python 3.12.x:

```bash
python3.12 -m venv .venv
```

### 3. Activate the Virtual Environment

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

### 4. Upgrade pip

```bash
pip install --upgrade pip
```

### 5. Install Dependencies

Install both runtime and development dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 6. Install the Package in Editable Mode

```bash
pip install -e .
```

### 7. Initialize Pre-commit Hooks

Set up pre-commit hooks to automatically format and lint your code:

```bash
pre-commit install
```

To manually run pre-commit on all files:

```bash
pre-commit run --all-files
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
mypy zamp_public_workflow_sdk/
```

### Linting

Run linting with ruff:

```bash
ruff check zamp_public_workflow_sdk/
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
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Development dependencies
├── setup.py                    # Package setup
└── pyproject.toml             # Project configuration
```

## Building and Publishing

To build and publish the package to PyPI:

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build the package
python -m build

# Upload to PyPI (requires credentials)
python -m twine upload dist/*
```

## Troubleshooting

### Virtual Environment Issues

If you encounter issues with the virtual environment:

```bash
# Remove existing venv
rm -rf .venv

# Create new venv
python3.12 -m venv .venv
source .venv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt -r requirements-dev.txt
```


If you need to install Python 3.12.11, use:
- **macOS**: `brew install python@3.12`
- **Linux**: Use your package manager or pyenv
- **Windows**: Download from [python.org](https://www.python.org/downloads/)


## Contributing

1. Create a new branch for your feature/bugfix
2. Make your changes
3. Ensure all tests pass: `bash scripts/tests.sh`
4. Ensure pre-commit checks pass: `pre-commit run --all-files`
5. Commit your changes (pre-commit hooks will run automatically)
6. Push and create a pull request
