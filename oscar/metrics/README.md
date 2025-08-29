# Metrics Integration for OSCAR

Comprehensive metrics and analytics system providing insights into OpenSearch build, test, and release processes through conversational AI.

## Features

- **Multi-Agent Architecture**: Specialized agents for different metric domains
- **Real-time Analytics**: Live data from OpenSearch CI/CD pipelines
- **Conversational Interface**: Natural language queries for complex metrics
- **Data Deduplication**: Intelligent handling of duplicate test results
- **Cross-Reference Mapping**: Links between RC numbers, build numbers, and components

## Architecture

The metrics system uses specialized Bedrock agents:

- **Integration Test Agent** - Test results and RC build mapping
- **Build Metrics Agent** - Build status and component resolution
- **Release Metrics Agent** - Release readiness and promotion metrics
- **Metrics Lambda** (`oscar-metrics-agent`) - Data processing and retrieval

## Project Structure

```
metrics/
├── lambda_function.py          # Main Lambda handler with agent routing
├── metrics_handler.py          # Core metrics processing logic
├── query_builders.py           # OpenSearch query construction
├── helper_functions.py         # Component resolution and RC mapping
├── response_builder.py         # Response formatting for agents
├── aws_utils.py               # AWS service integrations
├── storage.py                 # Data persistence utilities
├── config.py                  # Configuration management
└── requirements.txt           # Python dependencies
```

## Available Functions

### Integration Test Agent
| Function | Purpose | Parameters |
|----------|---------|------------|
| `get_integration_test_metrics` | Test results with deduplication | `rc_numbers`, `components`, `integ_test_build_numbers` |
| `get_rc_build_mapping` | Map RC numbers to build numbers | `rc_numbers` |

### Build Metrics Agent
| Function | Purpose | Parameters |
|----------|---------|------------|
| `get_build_metrics` | Build status and results | `build_numbers`, `components` |
| `resolve_components_from_builds` | Map build numbers to components | `build_numbers` |

### Release Metrics Agent
| Function | Purpose | Parameters |
|----------|---------|------------|
| `get_release_metrics` | Release readiness metrics | `components`, `build_numbers` |

## Data Sources

### OpenSearch Clusters
- **Production**: `search-opensearch-prod-logs-*`
- **Staging**: `search-opensearch-staging-logs-*`
- **Test Results**: Integration test outcomes and build artifacts
- **Build Data**: Component builds, versions, and dependencies

### Metric Types
- **Test Results**: Pass/fail rates, test duration, failure analysis
- **Build Metrics**: Success rates, build times, artifact generation
- **Release Data**: Component readiness, promotion status, dependencies
- **Performance**: Query response times, system health indicators

## Usage Examples

### Integration Test Analysis
```
User: "Show me test results for RC 2.11.0-rc1 for OpenSearch and Dashboards"
Agent: [Queries integration test metrics with deduplication]
```

### Build Status Inquiry
```
User: "What components were built in build 5249?"
Agent: [Resolves build number to component list]
```

### Release Readiness Check
```
User: "Is version 2.11.0 ready for release?"
Agent: [Analyzes release metrics across all components]
```

## Configuration

### Environment Variables
```bash
# OpenSearch Configuration
OPENSEARCH_HOST=<opensearch-endpoint>
OPENSEARCH_USERNAME=<username>
OPENSEARCH_PASSWORD=<password>

# AWS Configuration
AWS_REGION=us-east-1
METRICS_LAMBDA_FUNCTION_NAME=oscar-metrics-agent

# Data Processing
MAX_QUERY_SIZE=10000
DEFAULT_TIME_RANGE=30d
```

## Key Features

### Intelligent Deduplication
- Removes duplicate test results from multiple runs
- Preserves latest results for accurate analysis
- Handles overlapping test suites and builds

### Cross-Reference Mapping
- Links RC numbers to specific build numbers
- Maps build numbers to component lists
- Resolves version dependencies across components

### Agent Specialization
- **Integration Test Agent**: Focuses on test result analysis
- **Build Metrics Agent**: Specializes in build and component data
- **Release Metrics Agent**: Handles release readiness assessment

## Development

### Adding New Metrics
1. Extend appropriate handler in `metrics_handler.py`
2. Add query logic in `query_builders.py`
3. Update agent function mappings in `lambda_function.py`
4. Update Lambda function with new metrics

### Agent Configuration
- Update agent instructions in Bedrock console
- Modify function schemas for new parameters
- Test with conversational queries

The metrics system provides comprehensive insights into OpenSearch development processes through natural language interfaces, enabling data-driven decisions for build, test, and release operations.