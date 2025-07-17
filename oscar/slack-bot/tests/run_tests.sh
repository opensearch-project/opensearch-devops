#!/bin/bash

# Run all tests with coverage report
cd "$(dirname "$0")/.."

# Check for required dependencies and install if missing
echo "Checking for required dependencies..."
MISSING_DEPS=0

# Check for pytest
if ! python -c "import pytest" 2>/dev/null; then
    echo "pytest not found, will install"
    MISSING_DEPS=1
fi

# Check for pytest-cov
if ! python -c "import pytest_cov" 2>/dev/null; then
    echo "pytest-cov not found, will install"
    MISSING_DEPS=1
fi

# Check for slack_bolt
if ! python -c "import slack_bolt" 2>/dev/null; then
    echo "slack_bolt not found, will install"
    MISSING_DEPS=1
fi

# Check for boto3
if ! python -c "import boto3" 2>/dev/null; then
    echo "boto3 not found, will install"
    MISSING_DEPS=1
fi

# Check for moto
if ! python -c "import moto" 2>/dev/null; then
    echo "moto not found, will install"
    MISSING_DEPS=1
fi

# Install missing dependencies if any
if [ $MISSING_DEPS -eq 1 ]; then
    echo "Installing missing dependencies..."
    pip install pytest pytest-cov slack_bolt boto3 moto
fi

# Run tests with coverage
echo "Running tests with coverage..."
python -m pytest tests/ -v --cov=oscar --cov-report=term-missing