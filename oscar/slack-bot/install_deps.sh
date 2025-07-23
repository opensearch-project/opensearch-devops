#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Script to install dependencies with security checks for urllib3

set -e  # Exit on error

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Explicitly install urllib3 at secure version to override any transitive dependencies
echo "Ensuring urllib3 is at secure version 2.5.0..."
pip install urllib3==2.5.0 --force-reinstall

# Verify the urllib3 version
echo "Verifying urllib3 version..."
URLLIB3_VERSION=$(pip show urllib3 | grep Version | cut -d ' ' -f 2)
if [ "$URLLIB3_VERSION" != "2.5.0" ]; then
    echo "ERROR: urllib3 version is $URLLIB3_VERSION, expected 2.5.0"
    echo "Security vulnerabilities CVE-2025-50181 and CVE-2025-50182 may still be present"
    exit 1
else
    echo "✅ urllib3 version 2.5.0 confirmed - security vulnerabilities addressed"
fi

echo "Dependencies installed successfully!"