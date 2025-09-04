"""
Agent configuration builder utility for constructing Bedrock agent configs from JSON files.
Handles loading, validation, and construction of agent configurations for CDK deployment.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class FoundationModel(Enum):
    """Supported foundation models for Bedrock agents."""
    CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    CLAUDE_3_5_HAIKU = "anthropic.claude-3-5-haiku-20241022-v1:0"
    CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"


@dataclass
class ActionGroupConfig:
    """Configuration for a Bedrock agent action group."""
    name: str
    description: str
    lambda_function_arn: str
    api_schema: Dict[str, Any]
    execution_role_arn: Optional[str] = None
    action_group_state: str = "ENABLED"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for CDK deployment."""
        return asdict(self)


@dataclass
class KnowledgeBaseConfig:
    """Configuration for knowledge base association."""
    knowledge_base_id: str
    knowledge_base_state: str = "ENABLED"
    description: Optional[str] = None
    retrieval_configuration: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for CDK deployment."""
        config = asdict(self)
        if not config.get('retrieval_configuration'):
            config['retrieval_configuration'] = {
                'vectorSearchConfiguration': {
                    'numberOfResults': 10,
                    'overrideSearchType': 'HYBRID'
                }
            }
        return config


@dataclass
class CollaboratorConfig:
    """Configuration for agent collaborator."""
    agent_id: str
    agent_version: str
    collaboration_role: str
    relay_conversation_history: str = "TO_COLLABORATOR"
    collaboration_instruction: str = ""
    collaborator_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for CDK deployment."""
        return asdict(self)


@dataclass
class GuardrailConfig:
    """Configuration for agent guardrails."""
    guardrail_identifier: str
    guardrail_version: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for CDK deployment."""
        return asdict(self)


@dataclass
class AgentConfig:
    """Complete configuration for a Bedrock agent."""
    agent_name: str
    description: str
    instructions: str
    foundation_model: str
    agent_id: Optional[str] = None
    primary_alias_id: Optional[str] = None
    action_groups: List[ActionGroupConfig] = None
    knowledge_bases: List[KnowledgeBaseConfig] = None
    collaborators: List[CollaboratorConfig] = None
    guardrails: Optional[GuardrailConfig] = None
    idle_session_ttl_in_seconds: int = 1800
    agent_resource_role_arn: Optional[str] = None
    customer_encryption_key_arn: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        """Initialize empty lists if None."""
        if self.action_groups is None:
            self.action_groups = []
        if self.knowledge_bases is None:
            self.knowledge_bases = []
        if self.collaborators is None:
            self.collaborators = []
        if self.tags is None:
            self.tags = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for CDK deployment."""
        config = {
            'agent_name': self.agent_name,
            'description': self.description,
            'instructions': self.instructions,
            'foundation_model': self.foundation_model,
            'idle_session_ttl_in_seconds': self.idle_session_ttl_in_seconds,
            'tags': self.tags
        }
        
        if self.agent_id:
            config['agent_id'] = self.agent_id
        if self.primary_alias_id:
            config['primary_alias_id'] = self.primary_alias_id
        if self.agent_resource_role_arn:
            config['agent_resource_role_arn'] = self.agent_resource_role_arn
        if self.customer_encryption_key_arn:
            config['customer_encryption_key_arn'] = self.customer_encryption_key_arn
        if self.guardrails:
            config['guardrails'] = self.guardrails.to_dict()
        
        # Always include these sections, even if empty
        config['action_groups'] = [ag.to_dict() for ag in self.action_groups] if self.action_groups else []
        config['knowledge_bases'] = [kb.to_dict() for kb in self.knowledge_bases] if self.knowledge_bases else []
        config['collaborators'] = [c.to_dict() for c in self.collaborators] if self.collaborators else []
        
        return config


class AgentConfigBuilder:
    """Builder class for constructing agent configurations from JSON files."""
    
    def __init__(self, configs_dir: str = "cdk/agents/configs"):
        """
        Initialize the agent configuration builder.
        
        Args:
            configs_dir: Directory containing agent configuration JSON files
        """
        self.configs_dir = Path(configs_dir)
        self.configs_dir.mkdir(parents=True, exist_ok=True)
    
    def load_agent_config(self, config_file: str) -> AgentConfig:
        """
        Load agent configuration from a JSON file.
        
        Args:
            config_file: Name of the configuration file (with or without .json extension)
            
        Returns:
            AgentConfig object
        """
        if not config_file.endswith('.json'):
            config_file += '.json'
        
        config_path = self.configs_dir / config_file
        
        if not config_path.exists():
            raise FileNotFoundError(f"Agent configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return self._build_agent_config(config_data)
    
    def save_agent_config(self, agent_config: AgentConfig, config_file: str) -> None:
        """
        Save agent configuration to a JSON file.
        
        Args:
            agent_config: AgentConfig object to save
            config_file: Name of the configuration file (with or without .json extension)
        """
        if not config_file.endswith('.json'):
            config_file += '.json'
        
        config_path = self.configs_dir / config_file
        
        with open(config_path, 'w') as f:
            json.dump(agent_config.to_dict(), f, indent=2)
    
    def _build_agent_config(self, config_data: Dict[str, Any]) -> AgentConfig:
        """
        Build AgentConfig object from dictionary data.
        
        Args:
            config_data: Dictionary containing agent configuration
            
        Returns:
            AgentConfig object
        """
        # Build action groups
        action_groups = []
        if 'action_groups' in config_data:
            for ag_data in config_data['action_groups']:
                action_groups.append(ActionGroupConfig(**ag_data))
        
        # Build knowledge bases
        knowledge_bases = []
        if 'knowledge_bases' in config_data:
            for kb_data in config_data['knowledge_bases']:
                knowledge_bases.append(KnowledgeBaseConfig(**kb_data))
        
        # Build collaborators
        collaborators = []
        if 'collaborators' in config_data:
            for collab_data in config_data['collaborators']:
                collaborators.append(CollaboratorConfig(**collab_data))
        
        # Build guardrails
        guardrails = None
        if 'guardrails' in config_data:
            guardrails = GuardrailConfig(**config_data['guardrails'])
        
        # Create agent config
        agent_config = AgentConfig(
            agent_name=config_data['agent_name'],
            description=config_data['description'],
            instructions=config_data['instructions'],
            foundation_model=config_data['foundation_model'],
            agent_id=config_data.get('agent_id'),
            primary_alias_id=config_data.get('primary_alias_id'),
            action_groups=action_groups,
            knowledge_bases=knowledge_bases,
            collaborators=collaborators,
            guardrails=guardrails,
            idle_session_ttl_in_seconds=config_data.get('idle_session_ttl_in_seconds', 1800),
            agent_resource_role_arn=config_data.get('agent_resource_role_arn'),
            customer_encryption_key_arn=config_data.get('customer_encryption_key_arn'),
            tags=config_data.get('tags', {})
        )
        
        return agent_config
    
    def validate_agent_config(self, agent_config: AgentConfig) -> bool:
        """
        Validate agent configuration for completeness and correctness.
        
        Args:
            agent_config: AgentConfig object to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        errors = []
        
        # Validate required fields
        if not agent_config.agent_name:
            errors.append("Agent name is required")
        if not agent_config.description:
            errors.append("Agent description is required")
        if not agent_config.instructions:
            errors.append("Agent instructions are required")
        if not agent_config.foundation_model:
            errors.append("Foundation model is required")
        
        # Validate foundation model
        valid_models = [model.value for model in FoundationModel]
        if agent_config.foundation_model not in valid_models:
            errors.append(f"Invalid foundation model. Must be one of: {valid_models}")
        
        # Validate action groups
        for i, action_group in enumerate(agent_config.action_groups):
            if not action_group.name:
                errors.append(f"Action group {i}: name is required")
            if not action_group.description:
                errors.append(f"Action group {i}: description is required")
            if not action_group.lambda_function_arn:
                errors.append(f"Action group {i}: lambda_function_arn is required")
            if not action_group.api_schema:
                errors.append(f"Action group {i}: api_schema is required")
        
        # Validate knowledge bases
        for i, kb in enumerate(agent_config.knowledge_bases):
            if not kb.knowledge_base_id:
                errors.append(f"Knowledge base {i}: knowledge_base_id is required")
        
        # Validate collaborators
        for i, collab in enumerate(agent_config.collaborators):
            if not collab.agent_id:
                errors.append(f"Collaborator {i}: agent_id is required")
            if not collab.agent_version:
                errors.append(f"Collaborator {i}: agent_version is required")
            if not collab.collaboration_role:
                errors.append(f"Collaborator {i}: collaboration_role is required")
        
        if errors:
            raise ValueError(f"Agent configuration validation failed: {'; '.join(errors)}")
        
        return True
    
    def list_agent_configs(self) -> List[str]:
        """
        List all available agent configuration files.
        
        Returns:
            List of configuration file names (without .json extension)
        """
        config_files = []
        for config_file in self.configs_dir.glob("*.json"):
            config_files.append(config_file.stem)
        return sorted(config_files)
    
    def create_template_config(self, agent_name: str, foundation_model: str = None) -> AgentConfig:
        """
        Create a template agent configuration.
        
        Args:
            agent_name: Name for the agent
            foundation_model: Foundation model to use (defaults to Claude 3.5 Sonnet)
            
        Returns:
            Template AgentConfig object
        """
        if foundation_model is None:
            foundation_model = FoundationModel.CLAUDE_3_5_SONNET.value
        
        return AgentConfig(
            agent_name=agent_name,
            description=f"Template configuration for {agent_name}",
            instructions="You are a helpful AI assistant. Please provide accurate and helpful responses.",
            foundation_model=foundation_model,
            tags={"Environment": "Development", "Project": "OSCAR"}
        )