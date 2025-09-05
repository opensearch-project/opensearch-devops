# OSCAR Knowledge Base Documents

This directory contains documentation files that are used to populate the Amazon Bedrock knowledge base for the OSCAR Slack bot.

## Current Knowledge Base Configuration

The current knowledge base has the following configuration:

- **Knowledge Base ID**: 5FBGMYGHPK
- **Name**: knowledge-base-OpenSearch-build-docs
- **Embedding Model**: Amazon Titan Embed Text v2
- **Storage**: OpenSearch Serverless
- **Data Source**: S3 bucket (oscar-opensearch-kb)
- **Chunking Strategy**: Fixed Size (8192 tokens with 20% overlap)
- **Parsing Strategy**: Bedrock Data Automation

## Document Types

The knowledge base supports various document formats:

- **Markdown (.md)**: Preferred for text-based documentation
- **PDF (.pdf)**: For formatted documents and publications
- **Text (.txt)**: For simple text files
- **HTML (.html)**: For web-based documentation
- **Microsoft Office (.docx, .xlsx, .pptx)**: For office documents

## Current Documents

The current knowledge base contains the following documents:

- Building-an-OpenSearch-and-OpenSearch-Dashboards-Distribution.md
- Home.md
- OpenSearch-Project-Build-System-Quick-Overview.md
- README.md
- Releasing-the-Distribution.md
- Testing-the-Distribution.md
- _Footer.md
- _Sidebar.md
- Additional documents in the build-src-workflows-readmes/ directory

## Adding Documents

To add new documents to the knowledge base:

1. Place the files in this directory or an appropriate subdirectory
2. Ensure the files are in a supported format
3. Redeploy the CDK stack to upload the new documents
4. Wait for the knowledge base to be reindexed

## Best Practices

For optimal knowledge base performance:

1. **Use Clear Titles**: Documents should have clear, descriptive titles
2. **Structure Content**: Use headings and sections to organize information
3. **Keep Files Focused**: Each file should cover a specific topic
4. **Use Metadata**: Include relevant metadata where possible
5. **Maintain Consistency**: Use consistent formatting and terminology

## Deployment

During CDK deployment, the contents of this directory are automatically uploaded to an S3 bucket and used to create or update the Amazon Bedrock knowledge base.

The deployment process:

1. Creates an S3 bucket
2. Uploads all files from this directory to the bucket
3. Configures the Amazon Bedrock knowledge base to use the S3 bucket as a data source
4. Sets up appropriate IAM permissions

## Sample Documents

This directory includes a sample document to demonstrate the format and structure expected by the knowledge base:

- `sample.md`: A simple example document

## Troubleshooting

If the knowledge base is not returning expected results:

1. Check that documents are properly formatted
2. Verify that files were successfully uploaded to S3
3. Ensure the knowledge base was properly indexed
4. Check the Bedrock console for any indexing errors