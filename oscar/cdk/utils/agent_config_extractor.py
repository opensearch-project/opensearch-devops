"""
Agent configuration extractor for extracting complete Bedrock agent configurations via AWS APIs.
Extracts agent metadata, instructions, action groups, and knowledge base associations.
Saves extracted configurations as editable JSON files in cdk/agents/configs/.
"""

import json
import boto3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from botocore.exceptions import ClientError, BotoCoreError
from agent_config_builder import AgentConfig, ActionGroupConfig, KnowledgeBaseConfig, CollaboratorConfig, GuardrailConfig


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of agent configuration extraction."""
    success: bool
    agent_config: Optional[AgentConfig] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class AgentConfigExtractor:
    """Extractor for Bedrock agent configurations via AWS APIs."""
    
    def __init__(self, region: str = None, configs_dir: str = "cdk/agents/configs"):
        """
        Initialize the agent configuration extractor.
        
        Args:
            region: AWS region (defaults to us-east-1)
            configs_dir: Directory to save extracted configurations
        """
        self.region = region or "us-east-1"
        self.configs_dir = Path(configs_dir)
        self.configs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize AWS clients
        try:
            self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.region)
            logger.info(f"Initialized Bedrock Agent client for region: {self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock Agent client: {e}")
            raise
    
    def extract_agent_config(self, agent_id: str, alias_id: str = None) -> ExtractionResult:
        """
        Extract complete agent configuration from AWS Bedrock.
        
        Args:
            agent_id: Bedrock agent ID
            alias_id: Agent alias ID (optional, will extract primary alias if not provided)
            
        Returns:
            ExtractionResult containing the extracted configuration
        """
        logger.info(f"Starting extraction for agent ID: {agent_id}")
        warnings = []
        
        try:
            # Get agent details
            agent_response = self.bedrock_agent_client.get_agent(agentId=agent_id)
            agent_data = agent_response['agent']
            
            logger.info(f"Retrieved agent: {agent_data['agentName']}")
            
            # Get primary alias if not provided
            if not alias_id:
                try:
                    aliases_response = self.bedrock_agent_client.list_agent_aliases(agentId=agent_id)
                    aliases = aliases_response.get('agentAliasSummaries', [])
                    
                    # Find primary alias
                    primary_alias = None
                    for alias in aliases:
                        if alias.get('agentAliasName') == 'TSTALIASID':  # Primary alias name
                            primary_alias = alias
                            break
                    
                    if primary_alias:
                        alias_id = primary_alias['agentAliasId']
                        logger.info(f"Found primary alias ID: {alias_id}")
                    else:
                        warnings.append("No primary alias found, using latest agent version")
                        
                except ClientError as e:
                    warnings.append(f"Could not retrieve aliases: {e}")
                    logger.warning(f"Could not retrieve aliases: {e}")
            
            # Use DRAFT version for extracting action groups and knowledge bases
            agent_version = "DRAFT"
            
            # Extract action groups
            action_groups = self._extract_action_groups(agent_id, agent_version)
            if not action_groups:
                warnings.append("No action groups found for agent")
            
            # Extract knowledge base associations
            knowledge_bases = self._extract_knowledge_bases(agent_id, agent_version)
            if not knowledge_bases:
                warnings.append("No knowledge base associations found for agent")
            
            # Extract collaborators (if any)
            collaborators = self._extract_collaborators(agent_id, agent_version)
            
            # Extract guardrails (if configured)
            guardrails = self._extract_guardrails(agent_data)
            
            # Build agent configuration - ensure all sections are present even if empty
            agent_config = AgentConfig(
                agent_name=agent_data['agentName'],
                description=agent_data.get('description', ''),
                instructions=agent_data.get('instruction', ''),
                foundation_model=agent_data.get('foundationModel', ''),
                agent_id=agent_id,
                primary_alias_id=alias_id,
                action_groups=action_groups if action_groups else [],
                knowledge_bases=knowledge_bases if knowledge_bases else [],
                collaborators=collaborators if collaborators else [],
                guardrails=guardrails,
                idle_session_ttl_in_seconds=agent_data.get('idleSessionTTLInSeconds', 1800),
                agent_resource_role_arn=agent_data.get('agentResourceRoleArn'),
                customer_encryption_key_arn=agent_data.get('customerEncryptionKeyArn'),
                tags=self._extract_tags(agent_id) or {}
            )
            
            logger.info(f"Successfully extracted configuration for agent: {agent_config.agent_name}")
            return ExtractionResult(
                success=True,
                agent_config=agent_config,
                warnings=warnings
            )
            
        except ClientError as e:
            error_msg = f"AWS API error extracting agent {agent_id}: {e}"
            logger.error(error_msg)
            return ExtractionResult(success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error extracting agent {agent_id}: {e}"
            logger.error(error_msg)
            return ExtractionResult(success=False, error_message=error_msg)
    
    def _extract_action_groups(self, agent_id: str, agent_version: str = "DRAFT") -> List[ActionGroupConfig]:
        """Extract action groups for the agent."""
        action_groups = []
        
        try:
            response = self.bedrock_agent_client.list_agent_action_groups(
                agentId=agent_id,
                agentVersion=agent_version
            )
            action_group_summaries = response.get('actionGroupSummaries', [])
            
            for summary in action_group_summaries:
                action_group_id = summary['actionGroupId']
                
                # Get detailed action group information
                detail_response = self.bedrock_agent_client.get_agent_action_group(
                    agentId=agent_id,
                    agentVersion=agent_version,
                    actionGroupId=action_group_id
                )
                
                action_group_data = detail_response['agentActionGroup']
                
                # Extract API schema
                api_schema = {}
                if 'apiSchema' in action_group_data:
                    schema_data = action_group_data['apiSchema']
                    if 'payload' in schema_data:
                        try:
                            api_schema = json.loads(schema_data['payload'])
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse API schema for action group {action_group_data['actionGroupName']}")
                            api_schema = {"error": "Could not parse API schema", "raw_payload": schema_data['payload']}
                    elif 's3' in schema_data:
                        # Schema is stored in S3
                        s3_info = schema_data['s3']
                        api_schema = {
                            "note": "API schema stored in S3",
                            "s3_bucket": s3_info.get('s3BucketName', ''),
                            "s3_key": s3_info.get('s3ObjectKey', '')
                        }
                else:
                    logger.warning(f"No API schema found for action group {action_group_data['actionGroupName']}")
                    api_schema = {"note": "No API schema available in extraction"}
                
                # Get Lambda function ARN
                lambda_function_arn = ""
                if 'actionGroupExecutor' in action_group_data:
                    executor = action_group_data['actionGroupExecutor']
                    if 'lambda' in executor:
                        lambda_function_arn = executor['lambda']
                
                action_group_config = ActionGroupConfig(
                    name=action_group_data['actionGroupName'],
                    description=action_group_data.get('description', ''),
                    lambda_function_arn=lambda_function_arn,
                    api_schema=api_schema,
                    execution_role_arn=action_group_data.get('executionRoleArn'),
                    action_group_state=action_group_data.get('actionGroupState', 'ENABLED')
                )
                
                action_groups.append(action_group_config)
                logger.info(f"Extracted action group: {action_group_config.name}")
                
        except ClientError as e:
            logger.warning(f"Could not extract action groups: {e}")
        
        return action_groups
    
    def _extract_knowledge_bases(self, agent_id: str, agent_version: str = "DRAFT") -> List[KnowledgeBaseConfig]:
        """Extract knowledge base associations for the agent."""
        knowledge_bases = []
        
        try:
            response = self.bedrock_agent_client.list_agent_knowledge_bases(
                agentId=agent_id,
                agentVersion=agent_version
            )
            kb_summaries = response.get('agentKnowledgeBaseSummaries', [])
            
            for summary in kb_summaries:
                kb_id = summary['knowledgeBaseId']
                
                # Get detailed knowledge base association
                detail_response = self.bedrock_agent_client.get_agent_knowledge_base(
                    agentId=agent_id,
                    agentVersion=agent_version,
                    knowledgeBaseId=kb_id
                )
                
                kb_data = detail_response['agentKnowledgeBase']
                
                kb_config = KnowledgeBaseConfig(
                    knowledge_base_id=kb_id,
                    knowledge_base_state=kb_data.get('knowledgeBaseState', 'ENABLED'),
                    description=kb_data.get('description', ''),
                    retrieval_configuration=kb_data.get('retrievalConfiguration', {
                        'vectorSearchConfiguration': {
                            'numberOfResults': 10,
                            'overrideSearchType': 'HYBRID'
                        }
                    })
                )
                
                knowledge_bases.append(kb_config)
                logger.info(f"Extracted knowledge base: {kb_id}")
                
        except ClientError as e:
            logger.warning(f"Could not extract knowledge bases: {e}")
        
        return knowledge_bases
    
    def _extract_collaborators(self, agent_id: str, agent_version: str = "DRAFT") -> List[CollaboratorConfig]:
        """Extract collaborator configurations for the agent."""
        collaborators = []
        
        try:
            # List agent collaborators
            response = self.bedrock_agent_client.list_agent_collaborators(
                agentId=agent_id,
                agentVersion=agent_version
            )
            
            collaborator_summaries = response.get('agentCollaboratorSummaries', [])
            
            for summary in collaborator_summaries:
                collaborator_id = summary['collaboratorId']
                
                # Get detailed collaborator information
                detail_response = self.bedrock_agent_client.get_agent_collaborator(
                    agentId=agent_id,
                    agentVersion=agent_version,
                    collaboratorId=collaborator_id
                )
                
                collaborator_data = detail_response['agentCollaborator']
                
                # Extract agent ID and version from alias ARN
                alias_arn = collaborator_data['agentDescriptor']['aliasArn']
                # ARN format: arn:aws:bedrock:region:account:agent-alias/AGENT_ID/ALIAS_ID
                arn_parts = alias_arn.split('/')
                collaborator_agent_id = arn_parts[-2] if len(arn_parts) >= 2 else ""
                collaborator_alias_id = arn_parts[-1] if len(arn_parts) >= 1 else ""
                
                collaborator_config = CollaboratorConfig(
                    agent_id=collaborator_agent_id,
                    agent_version=collaborator_alias_id,  # Using alias ID as version for now
                    collaboration_role=collaborator_data['collaboratorName'],
                    relay_conversation_history=collaborator_data.get('relayConversationHistory', 'TO_COLLABORATOR'),
                    collaboration_instruction=collaborator_data.get('collaborationInstruction', ''),
                    collaborator_name=collaborator_data['collaboratorName']
                )
                
                collaborators.append(collaborator_config)
                logger.info(f"Extracted collaborator: {collaborator_config.collaborator_name}")
                
        except ClientError as e:
            logger.debug(f"Could not extract collaborators (may not be configured): {e}")
        except Exception as e:
            logger.warning(f"Error extracting collaborators: {e}")
        
        return collaborators
    
    def _extract_guardrails(self, agent_data: Dict[str, Any]) -> Optional[GuardrailConfig]:
        """Extract guardrail configuration if present."""
        if 'guardrailConfiguration' in agent_data:
            guardrail_config = agent_data['guardrailConfiguration']
            return GuardrailConfig(
                guardrail_identifier=guardrail_config.get('guardrailIdentifier', ''),
                guardrail_version=guardrail_config.get('guardrailVersion', '')
            )
        return None
    
    def _extract_tags(self, agent_id: str) -> Dict[str, str]:
        """Extract tags for the agent."""
        try:
            response = self.bedrock_agent_client.list_tags_for_resource(
                resourceArn=f"arn:aws:bedrock:{self.region}:*:agent/{agent_id}"
            )
            return response.get('tags', {})
        except ClientError as e:
            logger.warning(f"Could not extract tags: {e}")
            return {}
    
    def save_extracted_config(self, agent_config: AgentConfig, filename: str = None) -> str:
        """
        Save extracted agent configuration to JSON file.
        
        Args:
            agent_config: AgentConfig object to save
            filename: Optional filename (defaults to agent name)
            
        Returns:
            Path to saved configuration file
        """
        if not filename:
            # Generate filename from agent name
            safe_name = agent_config.agent_name.lower().replace(' ', '-').replace('_', '-')
            filename = f"{safe_name}-extracted.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        config_path = self.configs_dir / filename
        
        # Convert to dictionary and save
        config_dict = agent_config.to_dict()
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2, sort_keys=True)
        
        logger.info(f"Saved extracted configuration to: {config_path}")
        return str(config_path)
    
    def extract_and_save_agent(self, agent_id: str, alias_id: str = None, filename: str = None) -> ExtractionResult:
        """
        Extract agent configuration and save to file in one operation.
        
        Args:
            agent_id: Bedrock agent ID
            alias_id: Agent alias ID (optional)
            filename: Output filename (optional)
            
        Returns:
            ExtractionResult with file path information
        """
        result = self.extract_agent_config(agent_id, alias_id)
        
        if result.success and result.agent_config:
            try:
                file_path = self.save_extracted_config(result.agent_config, filename)
                result.warnings.append(f"Configuration saved to: {file_path}")
            except Exception as e:
                result.success = False
                result.error_message = f"Failed to save configuration: {e}"
        
        return result
    
    def extract_multiple_agents(self, agent_configs: List[Dict[str, str]]) -> Dict[str, ExtractionResult]:
        """
        Extract configurations for multiple agents.
        
        Args:
            agent_configs: List of dicts with 'agent_id', optional 'alias_id' and 'filename'
            
        Returns:
            Dictionary mapping agent_id to ExtractionResult
        """
        results = {}
        
        for config in agent_configs:
            agent_id = config['agent_id']
            alias_id = config.get('alias_id')
            filename = config.get('filename')
            
            logger.info(f"Extracting configuration for agent: {agent_id}")
            result = self.extract_and_save_agent(agent_id, alias_id, filename)
            results[agent_id] = result
            
            if result.success:
                logger.info(f"Successfully extracted {agent_id}")
            else:
                logger.error(f"Failed to extract {agent_id}: {result.error_message}")
        
        return results
    
    def list_available_agents(self) -> List[Dict[str, str]]:
        """
        List all available Bedrock agents in the account.
        
        Returns:
            List of agent summaries with id, name, and status
        """
        try:
            response = self.bedrock_agent_client.list_agents()
            agents = []
            
            for agent_summary in response.get('agentSummaries', []):
                agents.append({
                    'agent_id': agent_summary['agentId'],
                    'agent_name': agent_summary['agentName'],
                    'agent_status': agent_summary['agentStatus'],
                    'description': agent_summary.get('description', ''),
                    'updated_at': agent_summary.get('updatedAt', '').isoformat() if agent_summary.get('updatedAt') else ''
                })
            
            return agents
            
        except ClientError as e:
            logger.error(f"Could not list agents: {e}")
            return []


def main():
    """Main function for command-line usage."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Extract Bedrock agent configurations')
    parser.add_argument('--agent-id', required=True, help='Bedrock agent ID to extract')
    parser.add_argument('--alias-id', help='Agent alias ID (optional)')
    parser.add_argument('--filename', help='Output filename (optional)')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--configs-dir', default='cdk/agents/configs', help='Output directory')
    parser.add_argument('--list-agents', action='store_true', help='List all available agents')
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = AgentConfigExtractor(region=args.region, configs_dir=args.configs_dir)
    
    if args.list_agents:
        print("Available Bedrock agents:")
        agents = extractor.list_available_agents()
        for agent in agents:
            print(f"  ID: {agent['agent_id']}")
            print(f"  Name: {agent['agent_name']}")
            print(f"  Status: {agent['agent_status']}")
            print(f"  Description: {agent['description']}")
            print(f"  Updated: {agent['updated_at']}")
            print()
        return
    
    # Extract agent configuration
    result = extractor.extract_and_save_agent(
        agent_id=args.agent_id,
        alias_id=args.alias_id,
        filename=args.filename
    )
    
    if result.success:
        print(f"Successfully extracted configuration for agent: {args.agent_id}")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
    else:
        print(f"Failed to extract configuration: {result.error_message}")
        exit(1)


if __name__ == "__main__":
    main()