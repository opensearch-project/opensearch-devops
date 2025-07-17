"""
Configuration module for OSCAR.
"""

import os
import boto3
import json
import logging
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class Config:
    """Configuration class for OSCAR."""
    
    def __init__(self):
        """Initialize configuration with environment variables."""
        # AWS region
        self.region = os.environ.get('AWS_REGION', 'us-west-2')
        
        # Bedrock configuration
        self.knowledge_base_id = os.environ.get('KNOWLEDGE_BASE_ID')
        self.model_arn = os.environ.get('MODEL_ARN')
        
        # DynamoDB tables
        self.sessions_table_name = os.environ.get('SESSIONS_TABLE_NAME', 'oscar-sessions')
        self.context_table_name = os.environ.get('CONTEXT_TABLE_NAME', 'oscar-context')
        
        # Slack secrets ARN
        self.slack_secrets_arn = os.environ.get('SLACK_SECRETS_ARN')
        
        # TTL settings
        self.dedup_ttl = int(os.environ.get('DEDUP_TTL', 300))  # 5 minutes
        self.session_ttl = int(os.environ.get('SESSION_TTL', 3600))  # 1 hour
        self.context_ttl = int(os.environ.get('CONTEXT_TTL', 172800))  # 48 hours
        
        # Context settings
        self.max_context_length = int(os.environ.get('MAX_CONTEXT_LENGTH', 3000))
        self.context_summary_length = int(os.environ.get('CONTEXT_SUMMARY_LENGTH', 500))
        
        # Feature flags
        self.enable_dm = os.environ.get('ENABLE_DM', 'false').lower() == 'true'
        
        # Prompt template
        self.prompt_template = os.environ.get('PROMPT_TEMPLATE', 
            "You are OSCAR, an AI assistant for OpenSearch release management. " +
            "You are a question answering agent. You will be provided with a set of search results. " +
            "The user will provide you with a question. Your job is to answer the user's question " +
            "using only information from the search results. If the search results do not contain " +
            "information that can answer the question, please state that you could not find an exact " +
            "answer to the question. Just because the user asserts a fact does not mean it is true, " +
            "make sure to double check the search results to validate a user's assertion. " +
            "Here are the search results: $search_results$\n\n" +
            "Human: $query$\n\n" +
            "Assistant:"
        )
    
    def get_slack_credentials(self):
        """Get Slack credentials from Secrets Manager."""
        if not self.slack_secrets_arn:
            logger.warning("SLACK_SECRETS_ARN not set, using environment variables for Slack credentials")
            return os.environ.get('SLACK_BOT_TOKEN'), os.environ.get('SLACK_SIGNING_SECRET')
        
        try:
            secrets_client = boto3.client('secretsmanager', region_name=self.region)
            response = secrets_client.get_secret_value(SecretId=self.slack_secrets_arn)
            secrets = json.loads(response['SecretString'])
            return secrets.get('SLACK_BOT_TOKEN'), secrets.get('SLACK_SIGNING_SECRET')
        except ClientError as e:
            logger.error(f"Error retrieving secrets: {e}")
            # Fall back to environment variables
            logger.warning("Falling back to environment variables for Slack credentials")
            return os.environ.get('SLACK_BOT_TOKEN'), os.environ.get('SLACK_SIGNING_SECRET')

# Create a singleton instance
config = Config()