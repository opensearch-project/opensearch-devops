# OSCAR Knowledge Base Documents

This directory contains documentation files that will be automatically ingested into the OSCAR Knowledge Base during deployment.

## Purpose

The Knowledge Base provides OSCAR agents with access to:
- Release management procedures and best practices
- System documentation and troubleshooting guides
- API documentation and integration guides
- Historical release information and lessons learned

## File Organization

Documents should be organized by category:
- `release_procedures/` - Release management workflows and procedures
- `system_docs/` - Technical documentation for OSCAR components
- `troubleshooting/` - Common issues and resolution guides
- `api_docs/` - API documentation and integration examples

## Supported Formats

The Knowledge Base supports the following document formats:
- Markdown (.md)
- Plain text (.txt)
- PDF documents (.pdf)
- Microsoft Word documents (.docx)

## Automatic Ingestion

During CDK deployment, all documents in this directory will be:
1. Uploaded to the Knowledge Base S3 bucket
2. Processed and chunked for vector search
3. Indexed with appropriate metadata
4. Made available to OSCAR agents for retrieval

## Document Guidelines

For optimal retrieval performance:
- Use clear, descriptive headings
- Include relevant keywords and terminology
- Keep documents focused on specific topics
- Use consistent formatting and structure
- Include examples and code snippets where appropriate

## Updating Documents

To update Knowledge Base content:
1. Add or modify documents in this directory
2. Run the Knowledge Base sync utility (will be created in later tasks)
3. The system will automatically re-index updated content

## Example Structure

```
knowledge_docs/
├── release_procedures/
│   ├── release_checklist.md
│   ├── rc_process.md
│   └── hotfix_procedure.md
├── system_docs/
│   ├── architecture_overview.md
│   ├── lambda_functions.md
│   └── bedrock_agents.md
├── troubleshooting/
│   ├── common_issues.md
│   ├── slack_integration.md
│   └── metrics_problems.md
└── api_docs/
    ├── jenkins_api.md
    ├── slack_api.md
    └── opensearch_queries.md
```

## Note

This directory is currently empty but will be populated with relevant documentation as part of the OSCAR CDK automation implementation.