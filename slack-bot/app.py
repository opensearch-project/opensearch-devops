"""
OSCAR - OpenSearch Conversational Automation for Release 

Lambda handler for Slack events.
"""

import logging
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from oscar.config import config
from oscar.slack_handler import SlackHandler
from oscar.storage import get_storage
from oscar.bedrock import get_knowledge_base

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get Slack credentials
slack_token, slack_signing_secret = config.get_slack_credentials()

# Initialize Slack app
app = App(
    token=slack_token,
    signing_secret=slack_signing_secret,
    process_before_response=True
)

# Initialize storage and knowledge base
storage = get_storage()
knowledge_base = get_knowledge_base()

# Initialize and register Slack handler
handler = SlackHandler(app, storage, knowledge_base)
handler.register_handlers()

# Lambda handler
def lambda_handler(event, context):
    """AWS Lambda handler for Slack events."""
    logger.info("Received event from API Gateway")
    
    # Handle URL verification challenge
    if event.get('body'):
        import json
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        # Check if this is a URL verification challenge
        if body.get('type') == 'url_verification':
            logger.info("Received URL verification challenge")
            return {
                'statusCode': 200,
                'body': json.dumps({'challenge': body['challenge']})
            }
    
    # Handle regular Slack events
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)