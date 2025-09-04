#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Prepare Lambda deployment assets with dependencies installed
# This script mimics the functionality of lambda_update_scripts but for CDK deployment

set -e

echo "🔄 Preparing Lambda deployment assets with dependencies..."

# Clean up any existing deployment assets
rm -rf lambda_assets
mkdir -p lambda_assets

# Function to prepare a Lambda asset
prepare_lambda_asset() {
    local source_dir=$1
    local asset_name=$2
    local handler_file=$3
    
    echo "📦 Preparing $asset_name from $source_dir..."
    
    # Create asset directory
    mkdir -p "lambda_assets/$asset_name"
    
    # Copy source code
    cp -r "$source_dir"/* "lambda_assets/$asset_name/"
    
    # Install dependencies if requirements.txt exists
    if [ -f "$source_dir/requirements.txt" ]; then
        echo "   Installing dependencies for $asset_name..."
        pip install -r "$source_dir/requirements.txt" -t "lambda_assets/$asset_name/" --upgrade --quiet
        
        # Verify critical dependencies were installed
        echo "   Verifying dependencies..."
        if [ "$asset_name" = "oscar-agent" ]; then
            # Check for slack_bolt and boto3
            if [ ! -d "lambda_assets/$asset_name/slack_bolt" ] && [ ! -d "lambda_assets/$asset_name/slack_sdk" ]; then
                echo "❌ Missing Slack dependencies for $asset_name"
                exit 1
            fi
        fi
        
        if [ ! -d "lambda_assets/$asset_name/boto3" ]; then
            echo "❌ Missing boto3 for $asset_name"
            exit 1
        fi
        
        echo "   ✅ Dependencies verified for $asset_name"
    else
        echo "   No requirements.txt found for $asset_name"
    fi
    
    # Clean up Python cache files
    find "lambda_assets/$asset_name" -name '*.pyc' -delete
    find "lambda_assets/$asset_name" -name '__pycache__' -type d -exec rm -rf {} + || true
    
    # Show package size
    local size=$(du -sh "lambda_assets/$asset_name" | cut -f1)
    echo "   ✅ $asset_name prepared (size: $size)"
}

# Function to prepare flattened communication handler asset
prepare_communication_handler_asset() {
    echo "📦 Preparing oscar-communication-handler with flattened structure..."
    
    # Create asset directory
    mkdir -p "lambda_assets/oscar-communication-handler"
    
    # Copy the lambda entry point to root (rename to lambda_function.py)
    cp "../oscar-agent/communication_handler/lambda_handler.py" "lambda_assets/oscar-communication-handler/lambda_function.py"
    
    # Copy ONLY essential communication handler files directly to root (flatten structure)
    echo "   📁 Flattening essential communication_handler files to root directory..."
    
    cp "../oscar-agent/communication_handler/message_handler.py" "lambda_assets/oscar-communication-handler/"
    cp "../oscar-agent/communication_handler/message_formatter.py" "lambda_assets/oscar-communication-handler/"
    cp "../oscar-agent/communication_handler/slack_client.py" "lambda_assets/oscar-communication-handler/"
    cp "../oscar-agent/communication_handler/response_builder.py" "lambda_assets/oscar-communication-handler/"
    cp "../oscar-agent/communication_handler/channel_utils.py" "lambda_assets/oscar-communication-handler/"
    
    # Copy context_storage.py (unified storage)
    cp "../oscar-agent/context_storage.py" "lambda_assets/oscar-communication-handler/"
    
    # Copy config.py (required dependency)
    cp "../oscar-agent/config.py" "lambda_assets/oscar-communication-handler/"
    
    echo "   ✅ Flattened essential files to root"
    
    # Create comprehensive requirements.txt for the Lambda function
    cat > "lambda_assets/oscar-communication-handler/requirements.txt" << EOF
# Core AWS and Slack dependencies
boto3>=1.34.0
botocore>=1.34.0
slack_sdk>=3.19.0

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
python-dotenv>=1.0.0
EOF
    
    # Install dependencies
    echo "   📦 Installing Python dependencies..."
    pip install -r "lambda_assets/oscar-communication-handler/requirements.txt" -t "lambda_assets/oscar-communication-handler/" --upgrade --quiet
    
    # Verify critical dependencies
    echo "   🔍 Verifying dependencies..."
    CRITICAL_DEPS=("slack_sdk" "boto3" "botocore" "requests")
    for dep in "${CRITICAL_DEPS[@]}"; do
        if [ ! -d "lambda_assets/oscar-communication-handler/$dep" ] && [ ! -d "lambda_assets/oscar-communication-handler/${dep//_/-}" ]; then
            echo "❌ Missing dependency: $dep"
            pip install "$dep" -t "lambda_assets/oscar-communication-handler/" --upgrade --quiet || {
                echo "❌ Failed to install $dep"
                exit 1
            }
        fi
    done
    
    echo "   ✅ Dependencies verified"
    
    # Clean up any conflicting directories
    rm -rf "lambda_assets/oscar-communication-handler/storage/" 2>/dev/null || true
    rm -rf "lambda_assets/oscar-communication-handler/communication_handler/" 2>/dev/null || true
    rm -rf "lambda_assets/oscar-communication-handler/communication/" 2>/dev/null || true
    
    # Verify critical files exist in flattened structure
    CRITICAL_FILES=("lambda_function.py" "config.py" "message_handler.py" "message_formatter.py" "slack_client.py" "response_builder.py" "channel_utils.py" "context_storage.py")
    for file in "${CRITICAL_FILES[@]}"; do
        if [ ! -f "lambda_assets/oscar-communication-handler/$file" ]; then
            echo "❌ Missing critical file: $file"
            exit 1
        fi
    done
    echo "   ✅ All critical files present in flattened structure"
    
    # Clean up Python cache files
    find "lambda_assets/oscar-communication-handler" -name '*.pyc' -delete
    find "lambda_assets/oscar-communication-handler" -name '__pycache__' -type d -exec rm -rf {} + || true
    
    # Show package size
    local size=$(du -sh "lambda_assets/oscar-communication-handler" | cut -f1)
    echo "   ✅ oscar-communication-handler prepared (size: $size)"
}

# Prepare all Lambda assets
prepare_lambda_asset "../oscar-agent" "oscar-agent" "app.py"
prepare_communication_handler_asset  # Special flattened structure for communication handler
prepare_lambda_asset "../jenkins" "jenkins" "lambda_function.py"  
prepare_lambda_asset "../metrics" "metrics" "lambda_function.py"

echo ""
echo "🎉 All Lambda assets prepared successfully!"
echo ""
echo "📋 Prepared Assets:"
ls -la lambda_assets/
echo ""
echo "📋 Communication Handler Structure (Flattened):"
ls -la lambda_assets/oscar-communication-handler/ | head -10
echo ""
echo "💡 CDK will now use these pre-built assets for deployment"
echo "💡 Communication handler uses flattened structure for proper imports"