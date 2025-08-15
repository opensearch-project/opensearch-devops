#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Update all requirements.txt files with comprehensive dependencies

set -e

echo "📦 Updating all requirements.txt files with comprehensive dependencies..."

# Update OSCAR agent requirements
echo "📝 Updating oscar-agent/requirements.txt..."
cat > oscar-agent/requirements.txt << 'EOF'
# Core dependencies for Enhanced OSCAR Agent
slack-bolt>=1.18.0
boto3>=1.34.0
botocore>=1.34.0
slack_sdk>=3.19.0

# Additional dependencies for enhanced functionality
requests>=2.31.0
urllib3>=2.0.0

# Metrics integration dependencies
opensearch-py==2.4.2
aws-requests-auth==0.4.3

# Ensure we have all transitive dependencies
certifi>=2023.7.22
charset-normalizer>=3.0.0
idna>=3.0.0
python-dateutil>=2.8.0
jmespath>=1.0.0
s3transfer>=0.6.0
six>=1.16.0
EOF

# Update metrics requirements
echo "📝 Updating metrics/requirements.txt..."
cat > metrics/requirements.txt << 'EOF'
# Core AWS dependencies
boto3>=1.34.0
botocore>=1.34.0

# HTTP and networking
requests>=2.31.0
urllib3>=2.0.0

# Additional dependencies for metrics functionality
certifi>=2023.7.22
charset-normalizer>=3.0.0
idna>=3.0.0
python-dateutil>=2.8.0
jmespath>=1.0.0
s3transfer>=0.6.0
six>=1.16.0
EOF

# Update CDK lambda requirements (add actual dependencies)
echo "📝 Updating cdk/lambda/requirements.txt..."
cat > cdk/lambda/requirements.txt << 'EOF'
# Requirements file for OSCAR Slack Bot Lambda function
# 
# Core AWS and Slack dependencies
boto3>=1.34.0
botocore>=1.34.0
slack_sdk>=3.19.0
slack_bolt>=1.18.0

# HTTP and networking
requests>=2.31.0
urllib3>=2.0.0

# Additional dependencies
certifi>=2023.7.22
charset-normalizer>=3.0.0
idna>=3.0.0
python-dateutil>=2.8.0
jmespath>=1.0.0
s3transfer>=0.6.0
six>=1.16.0

# Note: These dependencies will be automatically installed during deployment
EOF

echo "✅ All requirements.txt files updated!"
echo ""
echo "📋 Updated files:"
echo "   ✅ oscar-agent/requirements.txt"
echo "   ✅ metrics/requirements.txt" 
echo "   ✅ cdk/lambda/requirements.txt"
echo ""
echo "📝 These files now contain comprehensive dependency lists that will be"
echo "   automatically installed during deployment by the deployment scripts."