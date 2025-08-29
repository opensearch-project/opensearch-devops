#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

# Test runner script for OSCAR bot

set -e

echo "🧪 Running OSCAR Bot Tests"
echo "=========================="

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test dependencies..."
    pip install -r tests/requirements.txt
fi

# Set PYTHONPATH to include source directories
export PYTHONPATH="${PYTHONPATH}:$(pwd)/oscar-agent:$(pwd)/metrics:$(pwd)"

# Disable config validation for testing
export DISABLE_CONFIG_VALIDATION=true

# Run tests with coverage
echo "Running unit tests with coverage..."
pytest tests/ \
    --cov=oscar-agent \
    --cov=metrics \
    --cov-report=html \
    --cov-report=term-missing \
    --verbose \
    --tb=short

echo ""
echo "✅ Tests completed!"
echo "📊 Coverage report generated in htmlcov/"
echo ""
echo "To run specific test files:"
echo "  pytest tests/test_config.py -v"
echo "  pytest tests/test_app.py -v"
echo "  pytest tests/test_storage.py -v"