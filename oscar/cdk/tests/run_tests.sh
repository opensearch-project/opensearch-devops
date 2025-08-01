#!/bin/bash

# Exit on error
set -e

# Change to the directory containing this script
cd "$(dirname "$0")"
cd ..

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install -r tests/requirements.txt

# Run tests
echo "Running tests..."
python -m pytest tests/ -v

# Deactivate virtual environment
deactivate

echo "Tests completed!"