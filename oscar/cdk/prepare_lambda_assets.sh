#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Dynamic Lambda Asset Preparation
# Generates Lambda deployment packages on-demand during CDK deployment

set -e

# Configuration
ASSETS_DIR="lambda_assets"
TEMP_DIR="/tmp/oscar_lambda_build_$$"

echo "🔄 Dynamically preparing Lambda deployment assets..."

# Clean up any existing deployment assets and temp directories
cleanup() {
    rm -rf "$ASSETS_DIR" 2>/dev/null || true
    rm -rf "$TEMP_DIR" 2>/dev/null || true
}

# Clean up only temp directory (preserve assets for CDK)
cleanup_temp() {
    rm -rf "$TEMP_DIR" 2>/dev/null || true
}

# Only cleanup temp directory on exit, not assets directory
cleanup_temp() {
    rm -rf "$TEMP_DIR" 2>/dev/null || true
}

# Trap to ensure temp cleanup on exit (but preserve assets)
trap cleanup_temp EXIT

# Create fresh directories
mkdir -p "$ASSETS_DIR"
mkdir -p "$TEMP_DIR"

# Function to prepare a Lambda asset with optimized dependency installation
prepare_lambda_asset() {
    local source_dir=$1
    local asset_name=$2
    local handler_file=$3
    
    echo "📦 Preparing $asset_name from $source_dir..."
    
    # Create temporary build directory
    local build_dir="$TEMP_DIR/$asset_name"
    mkdir -p "$build_dir"
    
    # Copy source code
    cp -r "$source_dir"/* "$build_dir/"
    
    # Install dependencies if requirements.txt exists
    if [ -f "$source_dir/requirements.txt" ]; then
        echo "   📦 Installing dependencies for $asset_name..."
        
        # Use pip with optimizations for faster, smaller installs
        pip install \
            -r "$source_dir/requirements.txt" \
            -t "$build_dir/" \
            --upgrade \
            --no-cache-dir \
            --no-compile \
            --disable-pip-version-check \
            --quiet
        
        # Verify critical dependencies were installed
        echo "   🔍 Verifying dependencies..."
        if [ "$asset_name" = "oscar-agent" ]; then
            # Check for slack_bolt and boto3
            if [ ! -d "$build_dir/slack_bolt" ] && [ ! -d "$build_dir/slack_sdk" ]; then
                echo "❌ Missing Slack dependencies for $asset_name"
                exit 1
            fi
        fi
        
        if [ ! -d "$build_dir/boto3" ]; then
            echo "❌ Missing boto3 for $asset_name"
            exit 1
        fi
        
        echo "   ✅ Dependencies verified for $asset_name"
    else
        echo "   ℹ️  No requirements.txt found for $asset_name"
    fi
    
    # Optimize package size
    echo "   🧹 Optimizing package size..."
    
    # Remove unnecessary files to reduce package size
    find "$build_dir" -name '*.pyc' -delete
    find "$build_dir" -name '*.pyo' -delete
    find "$build_dir" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name '*.dist-info' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name '*.egg-info' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name 'tests' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name 'test' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name '*.md' -delete 2>/dev/null || true
    find "$build_dir" -name '*.txt' -not -name 'requirements.txt' -delete 2>/dev/null || true
    
    # Move optimized package to final location
    mv "$build_dir" "$ASSETS_DIR/$asset_name"
    
    # Show package size
    local size=$(du -sh "$ASSETS_DIR/$asset_name" | cut -f1)
    echo "   ✅ $asset_name prepared (size: $size)"
}

# Function to prepare flattened communication handler asset with optimized build
prepare_communication_handler_asset() {
    echo "📦 Preparing oscar-communication-handler with flattened structure..."
    
    # Create temporary build directory
    local build_dir="$TEMP_DIR/oscar-communication-handler"
    mkdir -p "$build_dir"
    
    # Copy the lambda entry point to root (rename to lambda_function.py)
    cp "../oscar-agent/communication_handler/lambda_handler.py" "$build_dir/lambda_function.py"
    
    # Copy ONLY essential communication handler files directly to root (flatten structure)
    echo "   📁 Flattening essential communication_handler files to root directory..."
    
    cp "../oscar-agent/communication_handler/message_handler.py" "$build_dir/"
    cp "../oscar-agent/communication_handler/message_formatter.py" "$build_dir/"
    cp "../oscar-agent/communication_handler/slack_client.py" "$build_dir/"
    cp "../oscar-agent/communication_handler/response_builder.py" "$build_dir/"
    cp "../oscar-agent/communication_handler/channel_utils.py" "$build_dir/"
    
    # Copy context_storage.py (unified storage)
    cp "../oscar-agent/context_storage.py" "$build_dir/"
    
    # Copy config.py (required dependency)
    cp "../oscar-agent/config.py" "$build_dir/"
    
    echo "   ✅ Flattened essential files to root"
    
    # Create comprehensive requirements.txt for the Lambda function
    cat > "$build_dir/requirements.txt" << EOF
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
    
    # Install dependencies with optimizations
    echo "   📦 Installing Python dependencies..."
    pip install \
        -r "$build_dir/requirements.txt" \
        -t "$build_dir/" \
        --upgrade \
        --no-cache-dir \
        --no-compile \
        --disable-pip-version-check \
        --quiet
    
    # Verify critical dependencies
    echo "   🔍 Verifying dependencies..."
    CRITICAL_DEPS=("slack_sdk" "boto3" "botocore" "requests")
    for dep in "${CRITICAL_DEPS[@]}"; do
        if [ ! -d "$build_dir/$dep" ] && [ ! -d "$build_dir/${dep//_/-}" ]; then
            echo "❌ Missing dependency: $dep"
            pip install "$dep" -t "$build_dir/" --upgrade --no-cache-dir --quiet || {
                echo "❌ Failed to install $dep"
                exit 1
            }
        fi
    done
    
    echo "   ✅ Dependencies verified"
    
    # Clean up any conflicting directories
    rm -rf "$build_dir/storage/" 2>/dev/null || true
    rm -rf "$build_dir/communication_handler/" 2>/dev/null || true
    rm -rf "$build_dir/communication/" 2>/dev/null || true
    
    # Verify critical files exist in flattened structure
    CRITICAL_FILES=("lambda_function.py" "config.py" "message_handler.py" "message_formatter.py" "slack_client.py" "response_builder.py" "channel_utils.py" "context_storage.py")
    for file in "${CRITICAL_FILES[@]}"; do
        if [ ! -f "$build_dir/$file" ]; then
            echo "❌ Missing critical file: $file"
            exit 1
        fi
    done
    echo "   ✅ All critical files present in flattened structure"
    
    # Optimize package size
    echo "   🧹 Optimizing package size..."
    find "$build_dir" -name '*.pyc' -delete
    find "$build_dir" -name '*.pyo' -delete
    find "$build_dir" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name '*.dist-info' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name '*.egg-info' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name 'tests' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name 'test' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name '*.md' -delete 2>/dev/null || true
    find "$build_dir" -name '*.txt' -not -name 'requirements.txt' -delete 2>/dev/null || true
    
    # Move optimized package to final location
    mv "$build_dir" "$ASSETS_DIR/oscar-communication-handler"
    
    # Show package size
    local size=$(du -sh "$ASSETS_DIR/oscar-communication-handler" | cut -f1)
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
ls -la "$ASSETS_DIR/"
echo ""
echo "📋 Communication Handler Structure (Flattened):"
ls -la "$ASSETS_DIR/oscar-communication-handler/" | head -10
echo ""
echo "💡 CDK will now use these dynamically generated assets for deployment"
echo "💡 Communication handler uses flattened structure for proper imports"
echo "💡 Assets will be cleaned up automatically after deployment"

# Show total size savings
if command -v du >/dev/null 2>&1; then
    total_size=$(du -sh "$ASSETS_DIR" | cut -f1)
    echo "💾 Total package size: $total_size (generated on-demand)"
fi