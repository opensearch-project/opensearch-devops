#!/bin/bash

# Comprehensive Agent Deployment System with Dependency Management
# Handles Lambda updates, agent creation, and dependency linking

set -e

# Configuration
AWS_REGION="us-east-1"
CONFIG_FILE="deployment-config.json"
AGENT_IDS_FILE="deployed-agent-ids.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Initialize agent IDs tracking file
initialize_agent_ids() {
    if [[ ! -f "$AGENT_IDS_FILE" ]]; then
        echo '{}' > "$AGENT_IDS_FILE"
        log_info "Created agent IDs tracking file: $AGENT_IDS_FILE"
    fi
}

# Save agent ID to tracking file
# Update CDK .env file with agent IDs
update_cdk_env() {
    local agent_type=$1
    local agent_id=$2
    local alias_id=$3
    
    local env_file="cdk/.env"
    
    if [[ ! -f "$env_file" ]]; then
        log_warning "CDK .env file not found at $env_file"
        return 1
    fi
    
    # Map agent types to environment variable names
    case "$agent_type" in
        "oscar-privileged")
            sed -i.bak "s/^#.*OSCAR_PRIVILEGED_BEDROCK_AGENT_ID=.*/OSCAR_PRIVILEGED_BEDROCK_AGENT_ID=$agent_id/" "$env_file"
            sed -i.bak "s/^#.*OSCAR_PRIVILEGED_BEDROCK_AGENT_ALIAS_ID=.*/OSCAR_PRIVILEGED_BEDROCK_AGENT_ALIAS_ID=$alias_id/" "$env_file"
            ;;
        "oscar-limited")
            sed -i.bak "s/^#.*OSCAR_LIMITED_BEDROCK_AGENT_ID=.*/OSCAR_LIMITED_BEDROCK_AGENT_ID=$agent_id/" "$env_file"
            sed -i.bak "s/^#.*OSCAR_LIMITED_BEDROCK_AGENT_ALIAS_ID=.*/OSCAR_LIMITED_BEDROCK_AGENT_ALIAS_ID=$alias_id/" "$env_file"
            ;;
        "jenkins")
            sed -i.bak "s/^#.*JENKINS_AGENT_ID=.*/JENKINS_AGENT_ID=$agent_id/" "$env_file"
            sed -i.bak "s/^#.*JENKINS_AGENT_ALIAS_ID=.*/JENKINS_AGENT_ALIAS_ID=$alias_id/" "$env_file"
            ;;
        "build-metrics")
            # Add if not exists, update if exists
            if grep -q "BUILD_METRICS_AGENT_ID" "$env_file"; then
                sed -i.bak "s/^#*\s*BUILD_METRICS_AGENT_ID=.*/BUILD_METRICS_AGENT_ID=$agent_id/" "$env_file"
                sed -i.bak "s/^#*\s*BUILD_METRICS_AGENT_ALIAS_ID=.*/BUILD_METRICS_AGENT_ALIAS_ID=$alias_id/" "$env_file"
            else
                echo "BUILD_METRICS_AGENT_ID=$agent_id" >> "$env_file"
                echo "BUILD_METRICS_AGENT_ALIAS_ID=$alias_id" >> "$env_file"
            fi
            ;;
        "test-metrics")
            if grep -q "TEST_METRICS_AGENT_ID" "$env_file"; then
                sed -i.bak "s/^#*\s*TEST_METRICS_AGENT_ID=.*/TEST_METRICS_AGENT_ID=$agent_id/" "$env_file"
                sed -i.bak "s/^#*\s*TEST_METRICS_AGENT_ALIAS_ID=.*/TEST_METRICS_AGENT_ALIAS_ID=$alias_id/" "$env_file"
            else
                echo "TEST_METRICS_AGENT_ID=$agent_id" >> "$env_file"
                echo "TEST_METRICS_AGENT_ALIAS_ID=$alias_id" >> "$env_file"
            fi
            ;;
        "release-metrics")
            if grep -q "RELEASE_METRICS_AGENT_ID" "$env_file"; then
                sed -i.bak "s/^#*\s*RELEASE_METRICS_AGENT_ID=.*/RELEASE_METRICS_AGENT_ID=$agent_id/" "$env_file"
                sed -i.bak "s/^#*\s*RELEASE_METRICS_AGENT_ALIAS_ID=.*/RELEASE_METRICS_AGENT_ALIAS_ID=$alias_id/" "$env_file"
            else
                echo "RELEASE_METRICS_AGENT_ID=$agent_id" >> "$env_file"
                echo "RELEASE_METRICS_AGENT_ALIAS_ID=$alias_id" >> "$env_file"
            fi
            ;;
    esac
    
    # Clean up backup file
    rm -f "${env_file}.bak"
    
    log_info "Updated CDK .env with $agent_type agent IDs"
}

save_agent_id() {
    local agent_type=$1
    local agent_id=$2
    local alias_id=$3
    
    jq --arg type "$agent_type" --arg id "$agent_id" --arg alias "$alias_id" \
       '.[$type] = {"agent_id": $id, "alias_id": $alias}' \
       "$AGENT_IDS_FILE" > "${AGENT_IDS_FILE}.tmp" && mv "${AGENT_IDS_FILE}.tmp" "$AGENT_IDS_FILE"
    
    # Update CDK .env file
    update_cdk_env "$agent_type" "$agent_id" "$alias_id"
    
    log_success "Saved $agent_type agent ID: $agent_id"
}

# Get agent ID from tracking file
get_agent_id() {
    local agent_type=$1
    jq -r --arg type "$agent_type" '.[$type].agent_id // empty' "$AGENT_IDS_FILE"
}

# Check if Lambda function exists
check_lambda_exists() {
    local function_name=$1
    aws lambda get-function --region "$AWS_REGION" --function-name "$function_name" >/dev/null 2>&1
}

# Update agent configuration files with actual Lambda ARNs
update_lambda_arns() {
    local agent_type=$1
    
    log_info "Updating Lambda ARNs for $agent_type agent..."
    
    # Get Lambda function name from config
    local lambda_function=$(jq -r --arg type "$agent_type" '.agents[$type].lambda_function' "$CONFIG_FILE")
    
    if [[ "$lambda_function" != "null" ]]; then
        # Check if Lambda exists
        if check_lambda_exists "$lambda_function"; then
            local lambda_arn="arn:aws:lambda:$AWS_REGION:395380602281:function:$lambda_function"
            
            # Map agent type to placeholder pattern
            local placeholder=""
            case "$agent_type" in
                "jenkins")
                    placeholder="PLACEHOLDER_JENKINS_LAMBDA_ARN"
                    ;;
                "build-metrics")
                    placeholder="PLACEHOLDER_BUILD_METRICS_LAMBDA_ARN"
                    ;;
                "test-metrics")
                    placeholder="PLACEHOLDER_TEST_METRICS_LAMBDA_ARN"
                    ;;
                "release-metrics")
                    placeholder="PLACEHOLDER_RELEASE_METRICS_LAMBDA_ARN"
                    ;;
                "oscar-limited"|"oscar-privileged")
                    placeholder="PLACEHOLDER_SUPERVISOR_LAMBDA_ARN"
                    ;;
            esac
            
            # Update action group configuration
            if [[ -f "agent-configs/$agent_type/action-group.json" ]]; then
                if [[ -n "$placeholder" ]]; then
                    # Replace placeholder with actual ARN
                    jq --arg placeholder "$placeholder" --arg arn "$lambda_arn" \
                       'if .actionGroupExecutor.lambda == $placeholder then .actionGroupExecutor.lambda = $arn else . end' \
                       "agent-configs/$agent_type/action-group.json" > "agent-configs/$agent_type/action-group.json.tmp" && \
                       mv "agent-configs/$agent_type/action-group.json.tmp" "agent-configs/$agent_type/action-group.json"
                    log_success "Updated action group Lambda ARN for $agent_type ($placeholder -> $lambda_arn)"
                else
                    # Fallback for existing deployments
                    jq --arg arn "$lambda_arn" \
                       '.actionGroupExecutor.lambda = $arn' \
                       "agent-configs/$agent_type/action-group.json" > "agent-configs/$agent_type/action-group.json.tmp" && \
                       mv "agent-configs/$agent_type/action-group.json.tmp" "agent-configs/$agent_type/action-group.json"
                    log_success "Updated action group Lambda ARN for $agent_type"
                fi
            fi
            
            # Update action groups configuration (for privileged agent with multiple action groups)
            if [[ -f "agent-configs/$agent_type/action-groups.json" ]]; then
                # No supervisor Lambda ARN updates needed - oscar-enhanced-routing-v2 removed
                log_success "Updated routing action group Lambda ARN for $agent_type"
            fi
        else
            log_warning "Lambda function $lambda_function does not exist yet"
        fi
    fi
    
    # Update communication Lambda ARN for privileged agent
    if [[ "$agent_type" == "oscar-privileged" ]]; then
        local comm_lambda=$(jq -r --arg type "$agent_type" '.agents[$type].communication_lambda' "$CONFIG_FILE")
        if [[ "$comm_lambda" != "null" ]] && check_lambda_exists "$comm_lambda"; then
            local comm_arn="arn:aws:lambda:$AWS_REGION:395380602281:function:$comm_lambda"
            
            if [[ -f "agent-configs/$agent_type/action-groups.json" ]]; then
                jq --arg arn "$comm_arn" \
                   '(.[] | select(.actionGroupName == "communication-orchestration") | .actionGroupExecutor | select(.lambda == "PLACEHOLDER_COMMUNICATION_LAMBDA_ARN") | .lambda) = $arn' \
                   "agent-configs/$agent_type/action-groups.json" > "agent-configs/$agent_type/action-groups.json.tmp" && \
                   mv "agent-configs/$agent_type/action-groups.json.tmp" "agent-configs/$agent_type/action-groups.json"
                log_success "Updated communication Lambda ARN for $agent_type (PLACEHOLDER_COMMUNICATION_LAMBDA_ARN -> $comm_arn)"
            fi
        else
            log_warning "Communication Lambda function $comm_lambda does not exist yet"
        fi
    fi
}

# Update IAM policy with new agent alias ARNs
update_iam_policy_with_alias() {
    local agent_id=$1
    local alias_id=$2
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    local alias_arn="arn:aws:bedrock:${AWS_REGION}:${AWS_ACCOUNT_ID}:agent-alias/${agent_id}/${alias_id}"
    
    log_info "Adding alias ARN to IAM policy: $alias_arn"
    
    # Get current policy document
    local policy_arn="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/service-role/AmazonBedrockAgentsMultiAgentsPolicies_H5HG8S3OZG"
    local current_version=$(aws iam get-policy --policy-arn "$policy_arn" --query 'Policy.DefaultVersionId' --output text)
    
    # Get current policy document
    aws iam get-policy-version --policy-arn "$policy_arn" --version-id "$current_version" --query 'PolicyVersion.Document' > current_policy.json
    
    # Check if alias ARN already exists in policy
    if grep -q "$alias_arn" current_policy.json; then
        log_info "Alias ARN already exists in IAM policy"
        rm current_policy.json
        return 0
    fi
    
    # Add new alias ARN to the resource list
    jq --arg arn "$alias_arn" '.Statement[0].Resource += [$arn]' current_policy.json > updated_policy.json
    
    # Delete oldest non-default version if we have 5 versions
    local versions=$(aws iam list-policy-versions --policy-arn "$policy_arn" --query 'length(Versions)')
    if [[ $versions -ge 5 ]]; then
        local oldest_version=$(aws iam list-policy-versions --policy-arn "$policy_arn" --query 'Versions[?IsDefaultVersion==`false`] | sort_by(@, &CreateDate) | [0].VersionId' --output text)
        if [[ -n "$oldest_version" ]]; then
            aws iam delete-policy-version --policy-arn "$policy_arn" --version-id "$oldest_version"
            log_info "Deleted old policy version: $oldest_version"
        fi
    fi
    
    # Create new policy version
    aws iam create-policy-version \
        --policy-arn "$policy_arn" \
        --policy-document "file://updated_policy.json" \
        --set-as-default >/dev/null
    
    log_success "Updated IAM policy with new alias ARN: $alias_arn"
    
    # Cleanup
    rm current_policy.json updated_policy.json
}

# Update collaborator files with alias ARNs after agent deployment
update_collaborator_alias_arns() {
    local deployed_agent_type=$1
    local agent_id=$2
    local alias_id=$3
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    local alias_arn="arn:aws:bedrock:${AWS_REGION}:${AWS_ACCOUNT_ID}:agent-alias/${agent_id}/${alias_id}"
    
    log_info "Updating collaborator files with alias ARN for $deployed_agent_type..."
    
    # Find all collaborator files that might reference this agent
    for collaborator_file in agent-configs/*/collaborators.json; do
        if [[ -f "$collaborator_file" ]]; then
            # Check if this file contains the agent ID we just deployed
            if grep -q "\"agentId\": \"$agent_id\"" "$collaborator_file" 2>/dev/null; then
                log_info "Updating $collaborator_file with alias ARN for $deployed_agent_type"
                
                # Update the collaborator file to use aliasArn instead of agentId/agentVersion
                jq --arg agent_id "$agent_id" --arg alias_arn "$alias_arn" \
                   '(.[] | select(.agentDescriptor.agentId == $agent_id) | .agentDescriptor) = {"aliasArn": $alias_arn}' \
                   "$collaborator_file" > "${collaborator_file}.tmp" && \
                   mv "${collaborator_file}.tmp" "$collaborator_file"
                
                log_success "Updated $collaborator_file with alias ARN: $alias_arn"
            fi
        fi
    done
}

# Update collaborator agent IDs in configuration
update_collaborator_ids() {
    local agent_type=$1
    
    log_info "Updating collaborator IDs for $agent_type agent..."
    
    # Get collaborator dependencies
    local collaborators=$(jq -r --arg type "$agent_type" '.agents[$type].collaborators[]?' "$CONFIG_FILE")
    
    if [[ -f "agent-configs/$agent_type/collaborators.json" ]]; then
        local temp_file="agent-configs/$agent_type/collaborators.json.tmp"
        cp "agent-configs/$agent_type/collaborators.json" "$temp_file"
        
        for collaborator in $collaborators; do
            local collaborator_id=$(get_agent_id "$collaborator")
            if [[ -n "$collaborator_id" ]]; then
                # Map collaborator types to placeholder patterns and name patterns
                local placeholder=""
                local name_pattern=""
                case "$collaborator" in
                    "jenkins")
                        placeholder="PLACEHOLDER_JENKINS_AGENT_ID"
                        name_pattern="jenkins"
                        ;;
                    "build-metrics")
                        placeholder="PLACEHOLDER_BUILD_METRICS_AGENT_ID"
                        name_pattern="BuildMetrics"
                        ;;
                    "test-metrics")
                        placeholder="PLACEHOLDER_TEST_METRICS_AGENT_ID"
                        name_pattern="IntegrationTest"
                        ;;
                    "release-metrics")
                        placeholder="PLACEHOLDER_RELEASE_METRICS_AGENT_ID"
                        name_pattern="ReleaseReadiness"
                        ;;
                esac
                
                # Try to replace placeholder first
                local updated=false
                if [[ -n "$placeholder" ]]; then
                    local count=$(jq --arg placeholder "$placeholder" '[.[] | select(.agentDescriptor.agentId == $placeholder)] | length' "$temp_file")
                    if [[ "$count" -gt 0 ]]; then
                        jq --arg placeholder "$placeholder" --arg id "$collaborator_id" \
                           '(.[] | select(.agentDescriptor.agentId == $placeholder) | .agentDescriptor.agentId) = $id' \
                           "$temp_file" > "${temp_file}.new" && mv "${temp_file}.new" "$temp_file"
                        log_success "Updated $collaborator collaborator ID ($placeholder -> $collaborator_id)"
                        updated=true
                    fi
                fi
                
                # If placeholder replacement didn't work, try name-based matching
                if [[ "$updated" == false && -n "$name_pattern" ]]; then
                    local count=$(jq --arg pattern "$name_pattern" '[.[] | select(.collaboratorName | test($pattern; "i"))] | length' "$temp_file")
                    if [[ "$count" -gt 0 ]]; then
                        jq --arg pattern "$name_pattern" --arg id "$collaborator_id" \
                           '(.[] | select(.collaboratorName | test($pattern; "i")) | .agentDescriptor.agentId) = $id' \
                           "$temp_file" > "${temp_file}.new" && mv "${temp_file}.new" "$temp_file"
                        log_success "Updated $collaborator collaborator ID (name match: $name_pattern -> $collaborator_id)"
                        updated=true
                    fi
                fi
                
                if [[ "$updated" == false ]]; then
                    log_warning "Could not update collaborator $collaborator - no matching placeholder or name found"
                fi
            else
                log_warning "Collaborator $collaborator not found in deployed agents"
            fi
        done
        
        mv "$temp_file" "agent-configs/$agent_type/collaborators.json"
    fi
}

# Validate agent dependencies
validate_dependencies() {
    local agent_type=$1
    
    log_info "Validating dependencies for $agent_type agent..."
    
    # Check collaborator dependencies
    local collaborators=$(jq -r --arg type "$agent_type" '.agents[$type].collaborators[]?' "$CONFIG_FILE")
    local missing_deps=()
    
    for collaborator in $collaborators; do
        local collaborator_id=$(get_agent_id "$collaborator")
        if [[ -z "$collaborator_id" ]]; then
            missing_deps+=("$collaborator")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies for $agent_type: ${missing_deps[*]}"
        log_error "Please deploy dependencies first or run deployment in correct order"
        return 1
    fi
    
    # Check Lambda functions
    local lambda_function=$(jq -r --arg type "$agent_type" '.agents[$type].lambda_function' "$CONFIG_FILE")
    if [[ "$lambda_function" != "null" ]] && ! check_lambda_exists "$lambda_function"; then
        log_warning "Lambda function $lambda_function does not exist"
        log_warning "Agent will be created but action groups may fail until Lambda is deployed"
    fi
    
    # Check communication Lambda for privileged agent
    if [[ "$agent_type" == "oscar-privileged" ]]; then
        local comm_lambda=$(jq -r --arg type "$agent_type" '.agents[$type].communication_lambda' "$CONFIG_FILE")
        if [[ "$comm_lambda" != "null" ]] && ! check_lambda_exists "$comm_lambda"; then
            log_warning "Communication Lambda $comm_lambda does not exist"
            log_warning "Communication action group may fail until Lambda is deployed"
        fi
    fi
    
    log_success "Dependencies validated for $agent_type"
    return 0
}

# Deploy a single agent
deploy_agent() {
    local agent_type=$1
    
    log_info "Deploying $agent_type agent..."
    
    # Check if agent directory exists
    if [[ ! -d "agent-configs/$agent_type" ]]; then
        log_error "Agent configuration directory not found: agent-configs/$agent_type"
        return 1
    fi
    
    # Validate dependencies
    if ! validate_dependencies "$agent_type"; then
        return 1
    fi
    
    # Update collaborator IDs (Lambda ARNs already updated in Phase 1)
    update_collaborator_ids "$agent_type"
    
    # Create the agent
    log_info "Creating $agent_type agent..."
    AGENT_RESPONSE=$(aws bedrock-agent create-agent \
        --region "$AWS_REGION" \
        --cli-input-json "file://agent-configs/$agent_type/agent-config.json" \
        --output json)
    
    AGENT_ID=$(echo "$AGENT_RESPONSE" | jq -r '.agent.agentId')
    log_success "Created $agent_type agent with ID: $AGENT_ID"
    
    # Wait for agent to be ready
    log_info "Waiting for agent to be ready..."
    sleep 10
    
    # Create action group(s)
    if [[ -f "agent-configs/$agent_type/action-group.json" ]]; then
        log_info "Creating action group for $agent_type..."
        
        # Check if Lambda exists before creating action group
        local lambda_function=$(jq -r --arg type "$agent_type" '.agents[$type].lambda_function' "$CONFIG_FILE")
        if [[ "$lambda_function" != "null" ]] && check_lambda_exists "$lambda_function"; then
            aws bedrock-agent create-agent-action-group \
                --region "$AWS_REGION" \
                --agent-id "$AGENT_ID" \
                --agent-version "DRAFT" \
                --cli-input-json "file://agent-configs/$agent_type/action-group.json"
            log_success "Action group created for $agent_type"
        else
            log_warning "Skipping action group creation - Lambda function $lambda_function not found"
            log_warning "Run update-agent-dependencies.sh after deploying Lambda functions"
        fi
    fi
    
    # Create multiple action groups (for privileged agent)
    if [[ -f "agent-configs/$agent_type/action-groups.json" ]]; then
        log_info "Creating action groups for $agent_type..."
        jq -c '.[]' "agent-configs/$agent_type/action-groups.json" | while read action_group; do
            action_group_name=$(echo "$action_group" | jq -r '.actionGroupName')
            echo "$action_group" > "temp_action_group.json"
            
            # Check Lambda function for each action group
            local should_create=true
            if [[ "$action_group_name" == "communication-orchestration" ]]; then
                local comm_lambda=$(jq -r --arg type "$agent_type" '.agents[$type].communication_lambda' "$CONFIG_FILE")
                if [[ "$comm_lambda" != "null" ]] && ! check_lambda_exists "$comm_lambda"; then
                    log_warning "Skipping $action_group_name - Lambda function $comm_lambda not found"
                    should_create=false
                fi
            # oscar-enhanced-routing-v2 action group removed - no longer needed
            fi
            
            if [[ "$should_create" == "true" ]]; then
                aws bedrock-agent create-agent-action-group \
                    --region "$AWS_REGION" \
                    --agent-id "$AGENT_ID" \
                    --agent-version "DRAFT" \
                    --cli-input-json "file://temp_action_group.json"
                
                log_success "Created action group: $action_group_name"
            fi
            
            rm "temp_action_group.json"
        done
    fi
    
    # Associate knowledge base
    if [[ -f "agent-configs/$agent_type/knowledge-base.json" ]]; then
        log_info "Associating knowledge base for $agent_type..."
        aws bedrock-agent associate-agent-knowledge-base \
            --region "$AWS_REGION" \
            --agent-id "$AGENT_ID" \
            --agent-version "DRAFT" \
            --cli-input-json "file://agent-configs/$agent_type/knowledge-base.json"
        log_success "Knowledge base associated for $agent_type"
    fi
    
    # Create collaborators
    if [[ -f "agent-configs/$agent_type/collaborators.json" ]]; then
        log_info "Creating collaborators for $agent_type..."
        
        # Wait for all collaborator agents to be fully ready
        log_info "Waiting for collaborator agents to be fully ready..."
        sleep 30
        
        # Get AWS account ID
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        
        jq -c '.[]' "agent-configs/$agent_type/collaborators.json" | while read collaborator; do
            collaborator_name=$(echo "$collaborator" | jq -r '.collaboratorName')
            
            # Check if collaborator already uses aliasArn format
            alias_arn=$(echo "$collaborator" | jq -r '.agentDescriptor.aliasArn // empty')
            
            if [[ -n "$alias_arn" ]]; then
                # Already in new format, use as-is
                echo "$collaborator" > "temp_collaborator.json"
                log_info "Using existing alias ARN for $collaborator_name: $alias_arn"
            else
                # Old format - convert agentId/agentVersion to aliasArn
                agent_id=$(echo "$collaborator" | jq -r '.agentDescriptor.agentId')
                
                # Get the alias ID for this agent from deployed-agent-ids.json
                alias_id=""
                if [[ -f "deployed-agent-ids.json" ]]; then
                    # Find the alias ID by matching the agent ID
                    alias_id=$(jq -r --arg agent_id "$agent_id" 'to_entries[] | select(.value.agent_id == $agent_id) | .value.alias_id' deployed-agent-ids.json 2>/dev/null || echo "")
                fi
                
                if [[ -n "$alias_id" && "$alias_id" != "null" ]]; then
                    # Convert to new format with aliasArn
                    alias_arn="arn:aws:bedrock:${AWS_REGION}:${AWS_ACCOUNT_ID}:agent-alias/${agent_id}/${alias_id}"
                    updated_collaborator=$(echo "$collaborator" | jq --arg alias_arn "$alias_arn" '.agentDescriptor = {"aliasArn": $alias_arn}')
                    echo "$updated_collaborator" > "temp_collaborator.json"
                    log_info "Converted to alias ARN for $collaborator_name: $alias_arn"
                else
                    # Cannot convert - this should not happen in proper deployment order
                    log_error "Could not find alias for agent $agent_id - collaborator $collaborator_name cannot be created"
                    continue
                fi
            fi
            
            aws bedrock-agent associate-agent-collaborator \
                --region "$AWS_REGION" \
                --agent-id "$AGENT_ID" \
                --agent-version "DRAFT" \
                --client-token "${collaborator_name}-$(date +%s)-$(uuidgen | head -c 8)" \
                --cli-input-json "file://temp_collaborator.json"
            
            log_success "Created collaborator: $collaborator_name"
            rm "temp_collaborator.json"
        done
        
        # Wait additional time for collaborators to be fully associated
        log_info "Waiting for collaborators to be fully associated..."
        sleep 10
    fi
    
    # Prepare the agent
    log_info "Preparing $agent_type agent..."
    aws bedrock-agent prepare-agent \
        --region "$AWS_REGION" \
        --agent-id "$AGENT_ID" \
        --output json >/dev/null
    
    # Wait for agent to be fully prepared before creating alias
    log_info "Waiting for agent to be fully prepared..."
    if [[ -f "agent-configs/$agent_type/collaborators.json" ]]; then
        # Supervisor agents with collaborators need a bit more time
        log_info "Supervisor agent detected - waiting for preparation..."
        sleep 20
    else
        # Regular agents need less time
        sleep 10
    fi
    
    # Verify agent is in PREPARED state before creating alias
    log_info "Verifying agent is ready for alias creation..."
    max_attempts=10
    attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        agent_status=$(aws bedrock-agent get-agent --agent-id "$AGENT_ID" --query 'agent.agentStatus' --output text)
        if [[ "$agent_status" == "PREPARED" ]]; then
            log_info "Agent is ready (status: $agent_status)"
            break
        else
            log_info "Agent not ready yet (status: $agent_status), waiting... (attempt $attempt/$max_attempts)"
            sleep 15
            ((attempt++))
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        log_warning "Agent may not be fully ready, but proceeding with alias creation..."
    fi
    
    # Create alias
    log_info "Creating alias for $agent_type agent..."
    ALIAS_RESPONSE=$(aws bedrock-agent create-agent-alias \
        --region "$AWS_REGION" \
        --agent-id "$AGENT_ID" \
        --agent-alias-name "live" \
        --description "Live alias for $agent_type agent" \
        --output json)
    
    ALIAS_ID=$(echo "$ALIAS_RESPONSE" | jq -r '.agentAlias.agentAliasId')
    log_success "Created alias for $agent_type: $ALIAS_ID"
    
    # Save agent and alias IDs
    save_agent_id "$agent_type" "$AGENT_ID" "$ALIAS_ID"
    
    # Update IAM policy with new alias ARN
    update_iam_policy_with_alias "$AGENT_ID" "$ALIAS_ID"
    
    # Update any collaborator files that reference this agent with the new alias ARN
    update_collaborator_alias_arns "$agent_type" "$AGENT_ID" "$ALIAS_ID"
    
    log_success "Successfully deployed $agent_type agent!"
}

# Update all Lambda ARNs across all agent configurations
update_all_lambda_arns() {
    log_info "=== PHASE 1: Updating all Lambda ARNs in configurations ==="
    
    local deployment_order=$(jq -r '.deployment_order[]' "$CONFIG_FILE")
    
    for agent_type in $deployment_order; do
        update_lambda_arns "$agent_type"
    done
    
    log_success "All Lambda ARNs updated in configurations"
}

# Update knowledge base IDs in supervisor agent configurations
update_knowledge_base_ids() {
    log_info "=== PHASE 2: Updating knowledge base IDs ==="
    
    # Get knowledge base ID from config
    local kb_id=$(jq -r '.knowledge_bases.["opensearch-docs"].id' "$CONFIG_FILE")
    
    if [[ "$kb_id" != "null" ]] && [[ -n "$kb_id" ]]; then
        # Update knowledge base configurations for supervisor agents
        for agent_type in "oscar-limited" "oscar-privileged"; do
            if [[ -f "agent-configs/$agent_type/knowledge-base.json" ]]; then
                # Replace placeholder with actual knowledge base ID
                jq --arg kb_id "$kb_id" \
                   'if .knowledgeBaseId == "PLACEHOLDER_KNOWLEDGE_BASE_ID" then .knowledgeBaseId = $kb_id else . end' \
                   "agent-configs/$agent_type/knowledge-base.json" > "agent-configs/$agent_type/knowledge-base.json.tmp" && \
                   mv "agent-configs/$agent_type/knowledge-base.json.tmp" "agent-configs/$agent_type/knowledge-base.json"
                log_success "Updated knowledge base ID for $agent_type (PLACEHOLDER_KNOWLEDGE_BASE_ID -> $kb_id)"
            fi
        done
    else
        log_warning "Knowledge base ID not found in configuration - supervisor agents will be created without knowledge base"
    fi
}

# Main deployment function
main() {
    log_info "Starting comprehensive agent deployment..."
    
    # Initialize tracking
    initialize_agent_ids
    
    # PHASE 1: Update all Lambda ARNs first (before any agent creation)
    update_all_lambda_arns
    
    # PHASE 2: Update knowledge base IDs
    update_knowledge_base_ids
    
    # PHASE 3: Deploy agents in dependency order
    log_info "=== PHASE 3: Deploying agents in dependency order ==="
    
    local deployment_order=$(jq -r '.deployment_order[]' "$CONFIG_FILE")
    
    # Deploy agents in order
    for agent_type in $deployment_order; do
        log_info "=== Deploying $agent_type agent ==="
        
        # Check if agent already exists
        existing_id=$(get_agent_id "$agent_type")
        if [[ -n "$existing_id" ]]; then
            log_warning "$agent_type agent already deployed with ID: $existing_id"
            read -p "Do you want to redeploy? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Skipping $agent_type agent"
                continue
            fi
        fi
        
        deploy_agent "$agent_type"
        
        log_success "=== Completed $agent_type agent deployment ==="
        echo
    done
    
    log_success "All agents deployed successfully!"
    log_info "Agent IDs saved in: $AGENT_IDS_FILE"
    
    # Display summary
    echo
    echo "=== DEPLOYMENT SUMMARY ==="
    jq -r 'to_entries[] | "\(.key): \(.value.agent_id) (alias: \(.value.alias_id))"' "$AGENT_IDS_FILE"
}

# Run main function
main "$@"