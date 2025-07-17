"""
OSCAR - OpenSearch Conversational Automation for Release 

Legacy Socket mode app that was used for local development and testing.
"""

import os
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from oscar.config import config
from oscar.slack_handler import SlackHandler
from oscar.storage import get_storage
from oscar.bedrock import get_knowledge_base

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get Slack credentials
slack_token, slack_signing_secret = config.get_slack_credentials()
slack_app_token = os.environ.get("SLACK_APP_TOKEN")

if not slack_app_token or not slack_token:
    logger.error("Missing required environment variables SLACK_APP_TOKEN or SLACK_BOT_TOKEN")
    exit(1)

# Initialize Slack app
app = App(
    token=slack_token,
    signing_secret=slack_signing_secret
)

# Initialize storage and knowledge base
# Use in-memory storage for local development
storage = get_storage(storage_type='memory')
knowledge_base = get_knowledge_base(kb_type='mock')

# Initialize and register Slack handler
handler = SlackHandler(app, storage, knowledge_base)
handler.register_handlers()

if __name__ == "__main__":
    # Start the Socket Mode handler
    logger.info("Starting OSCAR Slack Bot in Socket Mode...")
    SocketModeHandler(app, slack_app_token).start()