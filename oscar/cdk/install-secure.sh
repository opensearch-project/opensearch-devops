#!/bin/bash
# Secure installation script for OSCAR CDK dependencies
# Ensures urllib3 vulnerabilities CVE-2025-50181 and CVE-2025-50182 are addressed

set -e

echo "Installing CDK dependencies with security constraints..."

# Install dependencies with explicit version pinning
pip install -r requirements.txt

# Verify urllib3 version
URLLIB3_VERSION=$(pip show urllib3 | grep Version | cut -d' ' -f2)
echo "Installed urllib3 version: $URLLIB3_VERSION"

# Check if we have the secure version
if [[ "$URLLIB3_VERSION" == "2.5.0" ]]; then
    echo "✅ urllib3 is at secure version 2.5.0 - vulnerabilities resolved"
else
    echo "❌ urllib3 version $URLLIB3_VERSION may be vulnerable"
    echo "Expected version: 2.5.0"
    exit 1
fi

echo "✅ All CDK dependencies installed securely"