#!/bin/bash

set -euo pipefail
IFS=$'\n\t'

uv run python -m pytest tests/ zamp_public_workflow_sdk/ --cov=zamp_public_workflow_sdk --cov-report=xml --cov-report=term-missing
git fetch origin main:refs/remotes/origin/main
uv run diff-cover --version

LINES_CHANGED=$(git diff --stat origin/main | tail -1 | awk '{print $4}' | sed 's/,//')


if [ "$LINES_CHANGED" -gt 30 ]; then
    uv run diff-cover coverage.xml --include-untracked --exclude tests/* --exclude sample/* --fail-under=85
else
    uv run diff-cover coverage.xml --include-untracked --exclude tests/* --exclude sample/* --fail-under=0
fi
