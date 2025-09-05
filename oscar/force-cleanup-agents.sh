#!/bin/bash
# Force cleanup all CDK agents with proper waiting

set -e

echo "🧹 Force cleaning up all CDK Bedrock agents..."

# Remaining agent IDs to clean up
AGENT_IDS=(
    "UBLSWGSLEA"  # build-metrics-agent-cdk
    "ZUHLP1FLJ7"  # integration-test-agent-cdk  
    "24OF04X4HP"  # jenkins-agent-cdk
    "WH1APYDGKS"  # release-metrics-agent-cdk
)

force_cleanup_agent() {
    local agent_id=$1
    echo "🔄 Force cleaning up agent: $agent_id"
    
    # Get agent name for logging
    local agent_name=$(aws bedrock-agent get-agent --agent-id "$agent_id" --query 'agent.agentName' --output text 2>/dev/null || echo "Unknown")
    echo "   Agent name: $agent_name"
    
    # Delete all aliases first with individual calls
    echo "   Deleting aliases individually..."
    local aliases=$(aws bedrock-agent list-agent-aliases --agent-id "$agent_id" --query 'agentAliasSummaries[].agentAliasId' --output text 2>/dev/null || echo "")
    
    if [[ -n "$aliases" ]]; then
        for alias_id in $aliases; do
            echo "     Deleting alias: $alias_id"
            aws bedrock-agent delete-agent-alias --agent-id "$agent_id" --agent-alias-id "$alias_id" 2>/dev/null || echo "     Already deleted or failed: $alias_id"
        done
        
        # Wait for all aliases to be deleted
        echo "   Waiting 30 seconds for aliases to be fully deleted..."
        sleep 30
        
        # Check if any aliases remain
        local remaining=$(aws bedrock-agent list-agent-aliases --agent-id "$agent_id" --query 'agentAliasSummaries[].agentAliasId' --output text 2>/dev/null || echo "")
        if [[ -n "$remaining" ]]; then
            echo "   ⚠️  Some aliases still remain: $remaining"
            echo "   Waiting another 30 seconds..."
            sleep 30
        fi
    else
        echo "     No aliases found"
    fi
    
    # Delete the agent
    echo "   Deleting agent..."
    if aws bedrock-agent delete-agent --agent-id "$agent_id" >/dev/null 2>&1; then
        echo "   ✅ Successfully deleted agent: $agent_name ($agent_id)"
    else
        echo "   ❌ Failed to delete agent: $agent_name ($agent_id)"
        echo "   Checking if agent still exists..."
        if aws bedrock-agent get-agent --agent-id "$agent_id" >/dev/null 2>&1; then
            echo "   Agent still exists, will try again later"
        else
            echo "   Agent no longer exists"
        fi
    fi
    
    echo ""
}

# Clean up each agent
for agent_id in "${AGENT_IDS[@]}"; do
    if aws bedrock-agent get-agent --agent-id "$agent_id" >/dev/null 2>&1; then
        force_cleanup_agent "$agent_id"
    else
        echo "🔍 Agent $agent_id not found or already deleted"
    fi
done

echo "🎉 Force cleanup completed!"
echo ""
echo "📋 Remaining agents:"
aws bedrock-agent list-agents --query 'agentSummaries[?contains(agentName, `cdk`)].{Name:agentName,ID:agentId}' --output table || echo "No CDK agents remaining"