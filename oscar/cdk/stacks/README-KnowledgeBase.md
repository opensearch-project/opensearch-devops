# OSCAR Knowledge Base Stack

This document describes the OSCAR Knowledge Base stack implementation, which provides automated document ingestion and vector search capabilities for the OSCAR Slack Bot.

## Overview

The Knowledge Base stack creates and manages:

- **S3 Bucket**: Document storage with versioning and lifecycle policies
- **OpenSearch Serverless Collection**: Vector search capabilities with encryption
- **Bedrock Knowledge Base**: Document ingestion pipeline with Titan embeddings
- **Lambda Function**: Automatic synchronization when documents are updated
- **IAM Roles**: Least-privilege access for all components

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   S3 Bucket     │    │  OpenSearch      │    │  Bedrock Knowledge  │
│  (Documents)    │───▶│  Serverless      │───▶│      Base           │
│                 │    │  Collection      │    │                     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                                               │
         │ S3 Events                                     │
         ▼                                               ▼
┌─────────────────┐                              ┌─────────────────────┐
│  Lambda Function│                              │  Bedrock Agents     │
│  (Auto Sync)    │                              │  (Query Interface)  │
└─────────────────┘                              └─────────────────────┘
```

## Components

### S3 Document Storage

- **Bucket Name**: `oscar-knowledge-docs-{account-id}-{region}`
- **Features**:
  - Versioning enabled for document history
  - Server-side encryption (S3 managed)
  - Lifecycle policies for cost optimization
  - Event notifications for automatic sync
  - Public access blocked for security

### OpenSearch Serverless Collection

- **Collection Name**: `oscar-knowledge-base-{environment}`
- **Features**:
  - Vector search optimized for embeddings
  - Encryption at rest with AWS managed keys
  - Network isolation (no public access)
  - Data access policies for least-privilege access

### Bedrock Knowledge Base

- **Name**: `oscar-knowledge-base-{environment}`
- **Features**:
  - Amazon Titan embeddings for vector generation
  - Automatic document chunking (300 tokens, 20% overlap)
  - Metadata extraction and indexing
  - Integration with Bedrock agents

### Document Sync Lambda

- **Function Name**: `oscar-document-sync-{environment}`
- **Features**:
  - Triggered by S3 events (create/update/delete)
  - Automatic Knowledge Base synchronization
  - Error handling and retry logic
  - CloudWatch logging for monitoring

## Usage

### Initial Deployment

1. Deploy the Knowledge Base stack as part of the main OSCAR deployment
2. Run the initial document ingestion script:

```bash
python cdk/scripts/ingest_knowledge_docs.py \
  --stack-name OscarSlackBotStack \
  --docs-dir cdk/knowledge_docs
```

### Document Management

#### Adding New Documents

1. Add markdown, text, or JSON files to `cdk/knowledge_docs/`
2. Run the ingestion script or upload directly to S3:

```bash
# Using the ingestion script
python cdk/scripts/ingest_knowledge_docs.py --stack-name OscarSlackBotStack

# Or using the document manager directly
python -m cdk.utils.document_manager \
  --bucket oscar-knowledge-docs-123456789012-us-east-1 \
  --kb-id ABCDEF123456 \
  --ds-id GHIJKL789012 \
  --action ingest
```

#### Monitoring Sync Status

```bash
python -m cdk.utils.document_manager \
  --bucket oscar-knowledge-docs-123456789012-us-east-1 \
  --kb-id ABCDEF123456 \
  --ds-id GHIJKL789012 \
  --action status
```

#### Listing Documents

```bash
python -m cdk.utils.document_manager \
  --bucket oscar-knowledge-docs-123456789012-us-east-1 \
  --kb-id ABCDEF123456 \
  --ds-id GHIJKL789012 \
  --action list
```

### Automatic Synchronization

The Knowledge Base automatically synchronizes when:

- Documents are added to the S3 bucket (in the `docs/` prefix)
- Documents are updated or deleted
- Supported file types: `.md`, `.txt`, `.rst`, `.json`

## Configuration

### Environment Variables

The stack uses these environment variables:

- `CDK_DEFAULT_ACCOUNT`: AWS account ID
- `CDK_DEFAULT_REGION`: AWS region (default: us-east-1)
- `ENVIRONMENT`: Environment name (dev/staging/prod)

### Document Processing

Documents are preprocessed before ingestion:

1. **Markdown Cleaning**: Normalize headers, remove HTML comments
2. **Whitespace Normalization**: Remove excessive whitespace
3. **Metadata Addition**: Add document metadata headers
4. **Chunking**: Split into 300-token chunks with 20% overlap

### Security

- All resources use least-privilege IAM policies
- S3 bucket blocks public access
- OpenSearch collection has network isolation
- Lambda function has scoped permissions
- Encryption at rest for all storage

## Monitoring

### CloudWatch Metrics

The stack provides these metrics:

- Lambda function invocations and errors
- S3 bucket operations
- Knowledge Base sync job status
- OpenSearch collection usage

### Logging

- Lambda function logs in CloudWatch
- S3 access logs (if enabled)
- Knowledge Base ingestion job logs

### Alerts

Configure CloudWatch alarms for:

- Lambda function errors
- Knowledge Base sync failures
- High S3 storage costs
- OpenSearch collection errors

## Troubleshooting

### Common Issues

1. **Sync Job Failures**
   - Check Lambda function logs
   - Verify IAM permissions
   - Ensure documents are in supported formats

2. **Document Not Found in Search**
   - Verify document was uploaded to `docs/` prefix
   - Check sync job status
   - Wait for indexing to complete (can take several minutes)

3. **Permission Errors**
   - Verify IAM roles have correct policies
   - Check OpenSearch data access policies
   - Ensure Bedrock model access is enabled

### Debug Commands

```bash
# Check stack outputs
aws cloudformation describe-stacks --stack-name OscarSlackBotStack \
  --query 'Stacks[0].Outputs'

# List S3 bucket contents
aws s3 ls s3://oscar-knowledge-docs-123456789012-us-east-1/docs/ --recursive

# Check Knowledge Base sync jobs
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ABCDEF123456 \
  --data-source-id GHIJKL789012

# View Lambda function logs
aws logs tail /aws/lambda/oscar-document-sync-dev --follow
```

## Cost Optimization

### S3 Storage

- Lifecycle policies transition old versions to cheaper storage classes
- Documents older than 90 days move to Glacier
- Incomplete multipart uploads are cleaned up after 7 days

### OpenSearch Serverless

- Standby replicas disabled for non-production environments
- Collection automatically scales based on usage
- No minimum capacity charges

### Lambda Function

- Right-sized memory allocation (256 MB)
- Short timeout (5 minutes) to avoid unnecessary charges
- Efficient code to minimize execution time

## Integration

### With Bedrock Agents

The Knowledge Base integrates with Bedrock agents through:

- Knowledge Base ID reference in agent configuration
- Retrieval configuration for search parameters
- Vector similarity search for relevant document chunks

### With OSCAR Components

- Agents query the Knowledge Base for documentation
- Slack bot provides document search capabilities
- Metrics functions can access knowledge for context

## Development

### Testing

Run the validation script:

```bash
python cdk/scripts/test_knowledge_base_stack.py
```

### Local Development

For local testing without AWS deployment:

```bash
# Test document preprocessing
python -c "
import sys
sys.path.append('cdk/utils')
from document_manager import DocumentManager
dm = DocumentManager.__new__(DocumentManager)
dm.supported_extensions = {'.md', '.txt'}
content = dm._preprocess_document('path/to/test.md')
print(content)
"
```

## Future Enhancements

- Support for additional document formats (PDF, DOCX)
- Advanced chunking strategies based on document structure
- Document versioning and change tracking
- Integration with external documentation sources
- Real-time document updates via webhooks