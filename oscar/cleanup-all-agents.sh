#!/bin/bash
# Clean up all CDK agents and their aliases

set -e

echo "🧹 Cleaning up all CDK Bedrock agents..."

# List of agent IDs to clean up
AGENT_IDS=(
    "UBLSWGSLEA"  # build-metrics-agent-cdk
    "ZUHLP1FLJ7"  # integration-test-agent-cdk  
    "24OF04X4HP"  # jenkins-agent-cdk
    "L2SLTX24C7"  # oscar-supervisor-agent-limited-cdk
    "TSCZE1WGWK"  # oscar-supervisor-agent-privileged-cdk
    "WH1APYDGKS"  # release-metrics-agent-cdk
)

cleanup_agent() {
    local agent_id=$1
    echo "🔄 Cleaning up agent: $agent_id"
    
    # Get agent name for logging
    local agent_name=$(aws bedrock-agent get-agent --agent-id "$agent_id" --query 'agent.agentName' --output text 2>/dev/null || echo "Unknown")
    echo "   Agent name: $agent_name"
    
    # Delete all aliases first
    echo "   Deleting aliases..."
    local aliases=$(aws bedrock-agent list-agent-aliases --agent-id "$agent_id" --query 'agentAliasSummaries[].agentAliasId' --output text 2>/dev/null || echo "")
    
    if [[ -n "$aliases" ]]; then
        for alias_id in $aliases; do
            echo "     Deleting alias: $alias_id"
            aws bedrock-agent delete-agent-alias --agent-id "$agent_id" --agent-alias-id "$alias_id" >/dev/null 2>&1 || echo "     Failed to delete alias $alias_id"
        done
        
        # Wait a bit for aliases to be deleted
        echo "   Waiting for aliases to be deleted..."
        sleep 5
    else
        echo "     No aliases found"
    fi
    
    # Delete the agent
    echo "   Deleting agent..."
    if aws bedrock-agent delete-agent --agent-id "$agent_id" >/dev/null 2>&1; then
        echo "   ✅ Successfully deleted agent: $agent_name ($agent_id)"
    else
        echo "   ❌ Failed to delete agent: $agent_name ($agent_id)"
    fi
    
    echo ""
}

# Clean up each agent
for agent_id in "${AGENT_IDS[@]}"; do
    if aws bedrock-agent get-agent --agent-id "$agent_id" >/dev/null 2>&1; then
        cleanup_agent "$agent_id"
    else
        echo "🔍 Agent $agent_id not found or already deleted"
    fi
done

echo "🎉 Agent cleanup completed!"
echo ""
echo "📋 Remaining agents:"
aws bedrock-agent list-agents --query 'agentSummaries[?contains(agentName, `cdk`)].{Name:agentName,ID:agentId}' --output table || echo "No CDK agents remaining"