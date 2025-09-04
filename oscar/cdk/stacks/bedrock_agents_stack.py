#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Bedrock Agents stack for OSCAR CDK automation.

This module defines the Bedrock agents infrastructure including:
- Privileged agent with full access capabilities and Claude 3.7 Sonnet
- Limited agent with read-only access and Claude 3.7 Sonnet
- Jenkins agent for CI/CD operations
- Metrics agents for integration tests, build metrics, and release metrics
- Action groups with proper Lambda function associations
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from aws_cdk import (
    Stack,
    Duration,
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_lambda as lambda_,
    CfnOutput
)
from constructs import Construct

# Configure logging
logger = logging.getLogger(__name__)


class OscarAgentsStack(Stack):
    """
    Bedrock agents infrastructure for OSCAR.
    
    This construct creates and configures Bedrock agents including:
    - Privileged agent with full access capabilities
    - Limited agent with read-only access
    - Jenkins agent for CI/CD operations
    - Metrics agents for test, build, and release analysis
    - Action groups with proper Lambda function associations
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        permissions_stack: Any,
        knowledge_base_stack: Any,
        lambda_stack: Any,
        **kwargs
    ) -> None:
        """
        Initialize Bedrock agents stack.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
            permissions_stack: The permissions stack with IAM roles
            knowledge_base_stack: The knowledge base stack
            lambda_stack: The Lambda functions stack
            **kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Store references to other stacks
        self.permissions_stack = permissions_stack
        self.knowledge_base_stack = knowledge_base_stack
        self.lambda_stack = lambda_stack
        
        # Get configuration from environment
        self.account_id = os.environ.get("CDK_DEFAULT_ACCOUNT")
        self.aws_region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
        self.env_name = os.environ.get("ENVIRONMENT", "dev")
        
        # Dictionary to store created agents
        self.agents: Dict[str, bedrock.CfnAgent] = {}
        self.agent_aliases: Dict[str, bedrock.CfnAgentAlias] = {}
        
        # Create agents
        self._create_basic_agents()
        
        # Create outputs
        self._create_outputs()
    
    def _create_basic_agents(self) -> None:
        """
        Create Bedrock agents using configurations from JSON files.
        """
        logger.info("Creating Bedrock agents from configuration files")
        
        # Get the agent execution role from permissions stack
        agent_role_arn = self.permissions_stack.bedrock_agent_role.role_arn
        
        # Define individual agent mappings (created first)
        individual_agent_mappings = [
            {
                "config_file": "jenkins-agent-current.json",
                "agent_name": "oscar-jenkins-agent-cdk-created", 
                "construct_id": "OscarJenkinsAgent",
                "alias_id": "OscarJenkinsAgentAlias",
                "agent_key": "jenkins"
            },
            {
                "config_file": "integration-test-agent-current.json",
                "agent_name": "oscar-test-metrics-agent-cdk-created",
                "construct_id": "OscarTestMetricsAgent", 
                "alias_id": "OscarTestMetricsAgentAlias",
                "agent_key": "test_metrics"
            },
            {
                "config_file": "build-metrics-agent-current.json",
                "agent_name": "oscar-build-metrics-agent-cdk-created",
                "construct_id": "OscarBuildMetricsAgent",
                "alias_id": "OscarBuildMetricsAgentAlias", 
                "agent_key": "build_metrics"
            },
            {
                "config_file": "release-metrics-agent-current.json",
                "agent_name": "oscar-release-metrics-agent-cdk-created",
                "construct_id": "OscarReleaseMetricsAgent",
                "alias_id": "OscarReleaseMetricsAgentAlias",
                "agent_key": "release_metrics"
            }
        ]
        
        # Define supervisor agent mappings (created after individual agents)
        supervisor_agent_mappings = [
            {
                "config_file": "oscar-privileged-agent-current.json",
                "agent_name": "oscar-privileged-agent-cdk-created",
                "construct_id": "OscarPrivilegedAgent",
                "alias_id": "OscarPrivilegedAgentAlias",
                "agent_key": "privileged"
            },
            {
                "config_file": "oscar-limited-agent-current.json", 
                "agent_name": "oscar-limited-agent-cdk-created",
                "construct_id": "OscarLimitedAgent",
                "alias_id": "OscarLimitedAgentAlias",
                "agent_key": "limited"
            }
        ]
        
        # Create individual agents first (no dependencies)
        logger.info("Creating individual agents (Jenkins and metrics agents)")
        for mapping in individual_agent_mappings:
            try:
                self._create_agent_from_config(mapping, agent_role_arn)
            except Exception as e:
                logger.error(f"Failed to create individual agent {mapping['agent_name']}: {e}")
                continue
        
        # Create supervisor agents second (depend on individual agents and knowledge base)
        logger.info("Creating supervisor agents (privileged and limited)")
        for mapping in supervisor_agent_mappings:
            try:
                self._create_agent_from_config(mapping, agent_role_arn)
            except Exception as e:
                logger.error(f"Failed to create agent {mapping['agent_name']}: {e}")
                continue
    
    def _create_agent_from_config(self, mapping: Dict[str, str], agent_role_arn: str) -> None:
        """
        Create a Bedrock agent from its JSON configuration file.
        
        Args:
            mapping: Configuration mapping with file paths and construct IDs
            agent_role_arn: IAM role ARN for the agent
        """
        config_path = os.path.join(os.path.dirname(__file__), "..", "agents", "configs", mapping["config_file"])
        
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            return
            
        try:
            # Load the configuration
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Replace dynamic IDs with actual CDK-created resource IDs
            config = self._replace_dynamic_ids(config, mapping["agent_key"])
            
            logger.info(f"Creating agent from config: {mapping['config_file']}")
            
            # Create action groups from config
            action_groups = []
            for ag_config in config.get("action_groups", []):
                # Update Lambda ARN to use CDK-created functions
                lambda_arn = self._get_lambda_arn_for_action_group(ag_config["name"])
                if lambda_arn:
                    action_group = bedrock.CfnAgent.AgentActionGroupProperty(
                        action_group_name=ag_config["name"],
                        description=ag_config["description"],
                        action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                            lambda_=lambda_arn
                        ),
                        action_group_state="ENABLED"
                    )
                    action_groups.append(action_group)
            
            # Create knowledge base associations from config
            knowledge_bases = []
            for kb_config in config.get("knowledge_bases", []):
                if kb_config.get("knowledge_base_id") and kb_config["knowledge_base_id"] != "CDK_KNOWLEDGE_BASE_ID":
                    knowledge_base = bedrock.CfnAgent.AgentKnowledgeBaseProperty(
                        knowledge_base_id=kb_config["knowledge_base_id"],
                        description=kb_config.get("description", "Knowledge base for OSCAR agent"),
                        knowledge_base_state=kb_config.get("knowledge_base_state", "ENABLED")
                    )
                    knowledge_bases.append(knowledge_base)
            
            # Create the agent with config values
            agent = bedrock.CfnAgent(
                self, mapping["construct_id"],
                agent_name=mapping["agent_name"],
                agent_resource_role_arn=agent_role_arn,
                description=config.get("description", "OSCAR agent"),
                foundation_model=config.get("foundation_model", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
                instruction=config.get("instructions", "You are an AI assistant for OpenSearch."),
                idle_session_ttl_in_seconds=config.get("idle_session_ttl_in_seconds", 1800),
                action_groups=action_groups if action_groups else None,
                knowledge_bases=knowledge_bases if knowledge_bases else None,
                auto_prepare=True
            )
            
            # Create agent alias
            alias = bedrock.CfnAgentAlias(
                self, mapping["alias_id"],
                agent_alias_name="LIVE",
                agent_id=agent.attr_agent_id,
                description=f"Live alias for {config.get('description', 'OSCAR agent')}"
            )
            
            # Store references
            self.agents[mapping["agent_key"]] = agent
            self.agent_aliases[mapping["agent_key"]] = alias
            
            # Store collaborator config for post-deployment setup
            if config.get("collaborators"):
                self._store_collaborator_config(mapping["agent_key"], config["collaborators"])
            
            logger.info(f"Successfully created agent: {mapping['agent_name']}")
            
        except Exception as e:
            logger.error(f"Failed to create agent from {mapping['config_file']}: {e}")
            raise
    
    def _get_lambda_arn_for_action_group(self, action_group_name: str) -> Optional[str]:
        """
        Get the Lambda ARN for a given action group name.
        
        Args:
            action_group_name: Name of the action group
            
        Returns:
            Lambda function ARN or None if not found
        """
        # Map action group names to Lambda function keys
        action_group_mappings = {
            "communication-orchestration": "communication_handler",
            "jenkins-operations": "jenkins_agent",
            "jenkins_operations": "jenkins_agent",
            "integration_test_action_group": "metrics_test_metrics",
            "build-metrics-group-agent": "metrics_build_metrics", 
            "release-metrics-group-agent": "metrics_release_metrics",
            "release-metrics-actions-group": "metrics_release_metrics"
        }
        
        lambda_key = action_group_mappings.get(action_group_name)
        if lambda_key and lambda_key in self.lambda_stack.lambda_functions:
            return self.lambda_stack.lambda_functions[lambda_key].function_arn
        
        logger.warning(f"No Lambda function found for action group: {action_group_name}")
        return None
    
    def _replace_dynamic_ids(self, config: Dict[str, Any], agent_key: str) -> Dict[str, Any]:
        """
        Replace dynamic placeholder IDs with actual CDK-created resource IDs.
        
        Args:
            config: Agent configuration dictionary
            agent_key: Key identifying the agent type
            
        Returns:
            Updated configuration with real resource IDs
        """
        # Create a deep copy to avoid modifying the original
        import copy
        updated_config = copy.deepcopy(config)
        
        # Only replace IDs for supervisor agents that have collaborators
        if agent_key in ["privileged", "limited"]:
            # Replace knowledge base IDs
            if "knowledge_bases" in updated_config:
                for kb in updated_config["knowledge_bases"]:
                    if kb.get("knowledge_base_id") == "CDK_KNOWLEDGE_BASE_ID":
                        if self.knowledge_base_stack and hasattr(self.knowledge_base_stack, 'knowledge_base') and self.knowledge_base_stack.knowledge_base:
                            kb["knowledge_base_id"] = self.knowledge_base_stack.knowledge_base.attr_knowledge_base_id
                            logger.info(f"Replaced knowledge base ID for {agent_key} agent")
                        else:
                            logger.warning(f"Knowledge base not available for {agent_key} agent - removing knowledge base configuration")
                            # Remove knowledge base configuration if not available
                            updated_config["knowledge_bases"] = []
            
            # Replace collaborator agent IDs
            if "collaborators" in updated_config:
                for collaborator in updated_config["collaborators"]:
                    agent_id_placeholder = collaborator.get("agent_id")
                    
                    # Map placeholder IDs to actual agent keys
                    id_mapping = {
                        "CDK_JENKINS_AGENT_ID": "jenkins",
                        "CDK_BUILD_METRICS_AGENT_ID": "build_metrics", 
                        "CDK_TEST_METRICS_AGENT_ID": "test_metrics",
                        "CDK_RELEASE_METRICS_AGENT_ID": "release_metrics"
                    }
                    
                    if agent_id_placeholder in id_mapping:
                        collaborator_key = id_mapping[agent_id_placeholder]
                        if collaborator_key in self.agents:
                            collaborator["agent_id"] = self.agents[collaborator_key].attr_agent_id
                            logger.info(f"Replaced {agent_id_placeholder} with actual agent ID for {agent_key} agent")
                        else:
                            logger.warning(f"Collaborator agent {collaborator_key} not found for {agent_key} agent")
        
        return updated_config
    
    def _store_collaborator_config(self, agent_key: str, collaborators: List[Dict[str, Any]]) -> None:
        """
        Store collaborator configuration for post-deployment setup.
        
        Args:
            agent_key: Key identifying the agent
            collaborators: List of collaborator configurations
        """
        if not hasattr(self, 'collaborator_configs'):
            self.collaborator_configs = {}
        
        self.collaborator_configs[agent_key] = collaborators
        logger.info(f"Stored collaborator config for {agent_key} agent with {len(collaborators)} collaborators")
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for the agents."""
        for agent_key, agent in self.agents.items():
            CfnOutput(
                self, f"Agent{agent_key.title()}Id",
                value=agent.attr_agent_id,
                description=f"ID of the {agent_key} OSCAR agent"
            )
            
            if agent_key in self.agent_aliases:
                alias = self.agent_aliases[agent_key]
                CfnOutput(
                    self, f"Agent{agent_key.title()}AliasId",
                    value=alias.attr_agent_alias_id,
                    description=f"Alias ID of the {agent_key} OSCAR agent"
                )