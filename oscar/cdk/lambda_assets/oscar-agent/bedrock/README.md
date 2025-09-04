# OSCAR Bedrock Agent Configuration Guide

This directory contains the Bedrock agent integration components for OSCAR. This guide explains how to configure AWS Bedrock agents for the OSCAR system, including the supervisor agent, specialist collaborators, and action groups.

## Architecture Overview

OSCAR uses a **Supervisor-Router** architecture with specialized collaborator agents:

```
┌─────────────────────────────────────────────────────────────┐
│                    OSCAR Supervisor Agent                   │
│                  (oscar-supervisor-agent)                   │
│                                                             │
│  • Intelligent routing between knowledge base & specialists │
│  • Communication orchestration                              │
│  • Context management and conversation flow                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────--┬─────────────────┬─────────────────────────┐
│   Knowledge       │   Specialist    │    Action Groups        │
│     Base          │  Collaborators  │                         │
│                   │                 │                         │
│ • Documentation   │ • BuildMetrics  │ • Communication         │
│ • Best Practices  │• IntegrationTest│   Orchestration         │
│ • Guides          │• ReleaseReadiness│ • Enhanced Routing     │
│ • Tutorials       │                 │                         │
└─────────────────--┴─────────────────┴─────────────────────────┘
```

## Supervisor Agent Configuration

### Basic Agent Settings

```json
{
  "agentName": "oscar-supervisor-agent",
  "description": "Supervisor Agent for OSCAR (OpenSearch Conversational Automation for Releases) with intelligent routing between knowledge base and metrics specialists.",
  "foundationModel": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v1:0",
  "agentCollaboration": "SUPERVISOR_ROUTER",
  "idleSessionTTLInSeconds": 600
}
```

### Agent Instructions

The supervisor agent uses comprehensive instructions for intelligent routing and response generation. Key sections include:

#### **Intelligent Routing Logic**
```
DOCUMENTATION QUERIES → Knowledge Base
- OpenSearch configuration, installation, APIs
- Best practices, troubleshooting guides
- Feature explanations, templates, tutorials

METRICS QUERIES → Specialist Collaborators  
- Integration test metrics → IntegrationTestSpecialist
- Build metrics → BuildAnalyzer
- Release metrics → ReleaseAnalyzer

HYBRID QUERIES → Knowledge Base + Collaborators
- "Based on best practices, how do our metrics compare?"
- "What does documentation recommend for our performance issues?"
```

#### **Automated Message Sending Workflow**
The agent includes a detailed 6-step workflow for processing message sending requests:

1. **Detect Message Sending Request** - Identify intent keywords
2. **Template Retrieval Search** - Search knowledge base for templates
3. **Data Collection** - Route to appropriate metrics specialists
4. **Template Filling** - Fill templates with real data
5. **User Verification** - Present message for user confirmation
6. **Final Function Call** - Send verified message

### Knowledge Base Integration

```json
{
  "knowledgeBaseId": "YOUR-KNOWLEDGE-BASE-ID",
  "description": "Use this for OpenSearch documentation, build commands, guides, release references, best practices, troubleshooting, & feature explanations. Prioritize for static information and how-to questions.",
  "knowledgeBaseState": "ENABLED"
}
```

## Action Groups

### 1. Communication Orchestration Action Group

**Purpose**: Handle automated message sending to Slack channels

```json
{
  "actionGroupName": "communication-orchestration",
  "description": "Send automated release management messages to Slack channels for authorized users",
  "actionGroupExecutor": {
    "lambda": "arn:aws:lambda:us-east-1:YOUR-ACCOUNT-ID:function:oscar-communication-handler"
  }
}
```

**Functions**:

#### `send_automated_message`
```json
{
  "name": "send_automated_message",
  "description": "Send automated messages to Slack channels for release management tasks. Processes natural language requests to generate and send templated messages.",
  "parameters": {
    "message_content": {
      "type": "string",
      "description": "Complete message content filled with actual data",
      "required": false
    },
    "target_channel": {
      "type": "string", 
      "description": "Target Slack channel ID or name",
      "required": false
    },
    "query": {
      "type": "string",
      "description": "The user's natural language request for sending a message",
      "required": false
    },
    "user_id": {
      "type": "string",
      "description": "Slack user ID of the person making the request for authorization",
      "required": false
    }
  }
}
```

#### `format_message_for_slack`
```json
{
  "name": "format_message_for_slack",
  "description": "Format a message from standard Markdown to Slack's mrkdwn syntax. Converts headings to bold text, fixes bold/italic formatting, converts links to Slack format, and handles mentions properly.",
  "parameters": {
    "message_content": {
      "type": "string",
      "description": "The message content in standard Markdown format that needs to be converted to Slack's mrkdwn syntax",
      "required": true
    }
  }
}
```

### 2. Enhanced Routing Action Group

**Purpose**: Process queries with intelligent routing between knowledge base and metrics specialists

```json
{
  "actionGroupName": "oscar-enhanced-routing-v2",
  "description": "Enhanced routing and coordination with knowledge base integration",
  "actionGroupExecutor": {
    "lambda": "arn:aws:lambda:us-east-1:YOUR-ACCOUNT-ID:function:oscar-supervisor-agent"
  }
}
```

**Functions**:

#### `process_oscar_query`
```json
{
  "name": "process_oscar_query",
  "description": "Process queries with intelligent routing between knowledge base and metrics specialists",
  "parameters": {
    "query": {
      "type": "string",
      "description": "User query for documentation, metrics analysis, or hybrid requests",
      "required": false
    },
    "context": {
      "type": "string",
      "description": "Additional context or conversation history", 
      "required": false
    },
    "query_type": {
      "type": "string",
      "description": "Query type hint: knowledge, metrics, hybrid, or auto",
      "required": false
    }
  }
}
```

## Collaborator Agents

### 1. BuildMetricsSpecialist

**Agent ID**: `YOUR-BUILD-AGENT-ID`  
**Alias ARN**: `arn:aws:bedrock:us-east-1:YOUR-ACCOUNT-ID:agent-alias/YOUR-BUILD-AGENT-ID/YOUR-ALIAS-ID`

**Collaboration Instructions**:
```
This BuildMetricsSpecialist agent specializes in build metrics, distribution build analysis, and build pipeline performance. It can analyze build failures, success rates, and component-specific build issues across different versions and time ranges. Collaborate with this BuildMetricsSpecialist for dynamic/analytical queries regarding Build Metrics.
```

**Core Capabilities**:
- Analyze build success rates, failure patterns, and component build performance
- Monitor distribution build results across different versions and RC numbers
- Evaluate build efficiency and identify problematic components
- Track build trends and component-specific build issues

**Data Sources**: `opensearch-distribution-build-results` index

### 2. IntegrationTestSpecialist

**Agent ID**: `YOUR-TEST-AGENT-ID`  
**Alias ARN**: `arn:aws:bedrock:us-east-1:YOUR-ACCOUNT-ID:agent-alias/YOUR-TEST-AGENT-ID/YOUR-ALIAS-ID`

**Collaboration Instructions**:
```
This IntegrationTestSpecialist agent specializes in integration test failures, RC-based analysis, and component testing patterns. It can analyze test failures across different platforms, architectures, and distributions. You provide detailed failure analysis with test reports and build URLs for debugging. Collaborate with this IntegrationTestSpecialist for dynamic/analytical queries regarding Test Metrics.
```

**Core Capabilities**:
- Integration test failure analysis
- RC-based testing analysis
- Component testing patterns
- Cross-platform test result analysis
- Detailed failure analysis with test reports and build URLs

**Data Sources**: `opensearch-integration-test-results` index

### 3. ReleaseReadinessSpecialist

**Agent ID**: `YOUR-RELEASE-AGENT-ID`  
**Alias ARN**: `arn:aws:bedrock:us-east-1:YOUR-ACCOUNT-ID:agent-alias/YOUR-RELEASE-AGENT-ID/YOUR-ALIAS-ID`

**Collaboration Instructions**:
```
This ReleaseReadinessSpecialist agent specializes in release readiness analysis, component release status, and release blocking issues. It can assess release readiness scores, identify components that need attention, and provide release owner information for coordination. Collaborate with this ReleaseReadinessSpecialist for dynamic/analytical queries regarding Release Metrics.
```

**Core Capabilities**:
- Release readiness analysis
- Component release status assessment
- Release blocking issue identification
- Release readiness scores
- Release owner information coordination

**Data Sources**: `opensearch_release_metrics` index

## Setting Up Your Own OSCAR Bedrock Configuration

### Step 1: Create the Supervisor Agent

1. **Create Agent**:
   ```bash
   aws bedrock-agent create-agent \
     --agent-name "oscar-supervisor-agent" \
     --description "Supervisor Agent for OSCAR with intelligent routing" \
     --foundation-model "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v1:0" \
     --agent-resource-role-arn "arn:aws:iam::YOUR-ACCOUNT-ID:role/AmazonBedrockExecutionRoleForAgents" \
     --idle-session-ttl-in-seconds 600 \
     --agent-collaboration "SUPERVISOR_ROUTER"
   ```

2. **Set Agent Instructions**: Use the comprehensive instructions from the current configuration (see agent instructions section above)

### Step 2: Create Specialist Agents

For each specialist (Build, Integration Test, Release Readiness):

1. **Create Agent**:
   ```bash
   aws bedrock-agent create-agent \
     --agent-name "build-metrics-agent" \
     --description "Enhanced build metrics agent for OpenSearch ecosystem" \
     --foundation-model "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v1:0" \
     --agent-resource-role-arn "arn:aws:iam::YOUR-ACCOUNT-ID:role/AmazonBedrockExecutionRoleForAgents"
   ```

2. **Set Specialist Instructions**: Each specialist needs domain-specific instructions for their data analysis capabilities

3. **Create Action Groups**: Each specialist needs action groups that connect to their respective Lambda functions

### Step 3: Configure Action Groups

#### Communication Orchestration Action Group

1. **Create Action Group**:
   ```bash
   aws bedrock-agent create-agent-action-group \
     --agent-id YOUR-SUPERVISOR-AGENT-ID \
     --agent-version DRAFT \
     --action-group-name "communication-orchestration" \
     --description "Send automated release management messages to Slack channels" \
     --action-group-executor lambda="arn:aws:lambda:us-east-1:YOUR-ACCOUNT-ID:function:oscar-communication-handler"
   ```

2. **Define Function Schema**: Use the JSON schema provided above for `send_automated_message` and `format_message_for_slack`

#### Enhanced Routing Action Group

1. **Create Action Group**:
   ```bash
   aws bedrock-agent create-agent-action-group \
     --agent-id YOUR-SUPERVISOR-AGENT-ID \
     --agent-version DRAFT \
     --action-group-name "oscar-enhanced-routing" \
     --description "Enhanced routing and coordination with knowledge base integration" \
     --action-group-executor lambda="arn:aws:lambda:us-east-1:YOUR-ACCOUNT-ID:function:oscar-supervisor-agent"
   ```

2. **Define Function Schema**: Use the JSON schema provided above for `process_oscar_query`

### Step 4: Add Collaborator Relationships

```bash
aws bedrock-agent create-agent-collaborator \
  --agent-id YOUR-SUPERVISOR-AGENT-ID \
  --agent-version DRAFT \
  --collaborator-name "BuildMetricsSpecialist" \
  --agent-descriptor alias-arn="arn:aws:bedrock:us-east-1:YOUR-ACCOUNT-ID:agent-alias/YOUR-BUILD-AGENT-ID/YOUR-BUILD-ALIAS-ID" \
  --collaboration-instruction "This BuildMetricsSpecialist agent specializes in build metrics, distribution build analysis, and build pipeline performance..." \
  --relay-conversation-history "TO_COLLABORATOR"
```

### Step 5: Associate Knowledge Base

```bash
aws bedrock-agent associate-agent-knowledge-base \
  --agent-id YOUR-SUPERVISOR-AGENT-ID \
  --agent-version DRAFT \
  --knowledge-base-id YOUR-KNOWLEDGE-BASE-ID \
  --description "Use this for OpenSearch documentation, build commands, guides, release references, best practices, troubleshooting, & feature explanations."
```

### Step 6: Prepare and Create Aliases

1. **Prepare Agent**:
   ```bash
   aws bedrock-agent prepare-agent \
     --agent-id YOUR-AGENT-ID
   ```

2. **Create Alias**:
   ```bash
   aws bedrock-agent create-agent-alias \
     --agent-id YOUR-AGENT-ID \
     --alias-name "production" \
     --agent-version "1"
   ```

## Configuration Best Practices

### Agent Instructions

1. **Be Specific**: Clearly define the agent's role and capabilities
2. **Include Routing Logic**: For supervisor agents, provide clear routing decision trees
3. **Define Response Guidelines**: Specify how agents should format and structure responses
4. **Include Workflow Steps**: For complex processes like message sending, provide step-by-step workflows

### Action Group Design

1. **Single Responsibility**: Each action group should have a focused purpose
2. **Clear Function Names**: Use descriptive names that indicate the function's purpose
3. **Comprehensive Parameters**: Include all necessary parameters with clear descriptions
4. **Optional Parameters**: Make parameters optional when possible to increase flexibility

### Collaborator Configuration

1. **Specialized Instructions**: Each collaborator should have domain-specific instructions
2. **Clear Collaboration Guidelines**: Define how the supervisor should interact with each collaborator
3. **Conversation History**: Use `TO_COLLABORATOR` to provide context to specialist agents
4. **Unique Names**: Use descriptive names that indicate the collaborator's specialty

### Security Considerations

1. **IAM Roles**: Use least-privilege IAM roles for agent execution
2. **Lambda Permissions**: Ensure Lambda functions have appropriate permissions for their data sources
3. **Authorization**: Implement user authorization in action group Lambda functions
4. **Data Access**: Restrict data access based on user permissions and roles

## Monitoring and Debugging

### CloudWatch Logs

Monitor agent performance through CloudWatch logs:
- Agent invocation logs
- Action group execution logs
- Lambda function logs
- Error and timeout tracking

### Agent Testing

Test your configuration with:
```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id YOUR-AGENT-ID \
  --agent-alias-id YOUR-ALIAS-ID \
  --session-id "test-session" \
  --input-text "Your test query here"
```

### Common Issues

1. **Permission Errors**: Check IAM roles and Lambda permissions
2. **Timeout Issues**: Adjust agent timeout settings and Lambda timeouts
3. **Routing Problems**: Review agent instructions and collaboration guidelines
4. **Data Access Issues**: Verify cross-account roles and VPC configurations

## Environment Variables

Ensure your Lambda functions have access to these environment variables:

```bash
# Required for all components
OSCAR_BEDROCK_AGENT_ID=YOUR-SUPERVISOR-AGENT-ID
OSCAR_BEDROCK_AGENT_ALIAS_ID=YOUR-SUPERVISOR-ALIAS-ID

# Required for metrics specialists
OPENSEARCH_HOST=https://your-opensearch-endpoint.region.es.amazonaws.com
METRICS_CROSS_ACCOUNT_ROLE_ARN=arn:aws:iam::YOUR-OPENSEARCH-ACCOUNT-ID:role/YourOpenSearchAccessRole

# Required for communication handler
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
AUTHORIZED_MESSAGE_SENDERS=U123456789,U987654321
CHANNEL_ALLOW_LIST=C123456789,C987654321
```

## Advanced Configuration

### Custom Prompt Templates

You can override default prompt templates for specific use cases:

```json
{
  "promptType": "ORCHESTRATION",
  "basePromptTemplate": "Your custom prompt template here...",
  "promptState": "ENABLED",
  "inferenceConfiguration": {
    "temperature": 1.0,
    "stopSequences": ["</answer>"]
  }
}
```

### Memory Configuration

Enable conversation memory for better context retention:

```json
{
  "memoryConfiguration": {
    "enabledMemoryTypes": ["SESSION_SUMMARY"],
    "storageDays": 30
  }
}
```

### Guardrails

Implement content filtering and safety measures:

```json
{
  "guardrailConfiguration": {
    "guardrailIdentifier": "YOUR-GUARDRAIL-ID",
    "guardrailVersion": "1"
  }
}
```

This configuration provides a robust, scalable foundation for the OSCAR system with intelligent routing, specialized analysis capabilities, and automated communication features.