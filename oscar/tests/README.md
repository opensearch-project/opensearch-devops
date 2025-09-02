# OSCAR Bot Tests

Comprehensive test suite for the OSCAR bot, covering unit tests for all major components.

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and test configuration
├── test_app.py                    # Main application handler tests
├── test_config.py                 # Configuration management tests
├── test_storage.py                # DynamoDB storage tests
├── test_slack_handler.py          # Slack integration tests
├── test_bedrock_agent.py          # Bedrock AI agent tests
├── test_communication_handler.py  # Message processing tests
├── test_metrics.py                # Analytics and monitoring tests
├── test_dynamodb_setup.py         # DynamoDB setup and table access tests
├── test_aws_connectivity.py       # AWS role assumption and OpenSearch connectivity tests
├── test_jenkins.py                # Comprehensive jenkins/ directory testing
├── requirements.txt               # Test dependencies
└── run_tests.sh                   # Test runner script
```

## Running Tests

### Quick Start
```bash
# Run all tests
./tests/run_tests.sh
```

### Individual Test Files
```bash
# Configuration tests
pytest tests/test_config.py -v

# Storage tests
pytest tests/test_storage.py -v

# Slack handler tests
pytest tests/test_slack_handler.py -v

# Bedrock agent tests
pytest tests/test_bedrock_agent.py -v
```

### With Coverage
```bash
pytest tests/ --cov=oscar-agent --cov=metrics --cov-report=html
```

## Test Categories

### Unit Tests
- **Configuration**: Environment variable handling, validation
- **Storage**: DynamoDB operations, context management
- **Slack Handler**: Event processing, message validation, authentication
- **Bedrock Agent**: AI processing, query handling, error management
- **Communication Handler**: Message formatting, response building
- **Metrics**: Analytics, data processing, reporting
- **DynamoDB Setup**: Table creation, access testing, configuration validation
- **AWS Connectivity**: Role assumption, OpenSearch connectivity, error handling

### Test Features
- **Mocking**: AWS services, Slack API, external dependencies
- **Fixtures**: Reusable test data and mock objects
- **Coverage**: Code coverage reporting with HTML output
- **Validation**: Input validation, error handling, edge cases

## Dependencies

Test dependencies are managed in `tests/requirements.txt`:
- `pytest`: Test framework
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Enhanced mocking capabilities
- `moto`: AWS service mocking
- `boto3`: AWS SDK (for integration tests)
- `slack-bolt`: Slack SDK (for integration tests)

## Test Configuration

Tests use `pytest.ini` for configuration:
- Test discovery patterns
- Marker definitions
- Output formatting
- Warning suppression

## Fixtures

Shared fixtures in `conftest.py`:
- `mock_env_vars`: Environment variable mocking
- `mock_slack_event`: Sample Slack event data
- `mock_lambda_context`: AWS Lambda context
- `mock_bedrock_client`: Bedrock service client
- `mock_dynamodb_table`: DynamoDB table operations

## Best Practices

- **Isolation**: Each test is independent and doesn't affect others
- **Mocking**: External services are mocked to avoid dependencies
- **Coverage**: Aim for high code coverage while focusing on critical paths
- **Readability**: Tests are clear and document expected behavior
- **Speed**: Unit tests run quickly for fast feedback
