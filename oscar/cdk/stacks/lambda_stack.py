#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
"""
Lambda stack for OSCAR infrastructure.

This module defines all Lambda functions used by OSCAR including:
- Main OSCAR agent with Slack event processing
- Communication handler for Bedrock action groups
- Jenkins agent for CI/CD integration
- Multiple metrics agents for different data sources
"""

import logging
import os
from typing import Dict, Any, Optional
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ec2 as ec2,
    CfnOutput
)
from constructs import Construct
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from lambda_assets import get_lambda_asset_path, prepare_lambda_assets

# Configure logging
logger = logging.getLogger(__name__)

class OscarLambdaStack(Stack):
    """
    Comprehensive Lambda resources for OSCAR infrastructure.
    
    This construct creates and configures all Lambda functions used by OSCAR:
    - Main OSCAR agent with Slack event processing capabilities
    - Communication handler for Bedrock action group integration
    - Jenkins agent for CI/CD operations
    - Multiple metrics agents for different data sources (test, build, release, deployment)
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        permissions_stack: Any,
        secrets_stack: Any,
        vpc_stack: Optional[Any] = None,
        **kwargs
    ) -> None:
        """
        Initialize Lambda resources.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
            permissions_stack: The permissions stack with IAM roles
            secrets_stack: The secrets stack with central environment secret
            vpc_stack: Optional VPC stack for VPC-enabled functions
            **kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Store references to other stacks
        self.permissions_stack = permissions_stack
        self.secrets_stack = secrets_stack
        self.vpc_stack = vpc_stack
        
        # Prepare Lambda assets dynamically
        logger.info("Preparing Lambda assets dynamically...")
        if not prepare_lambda_assets():
            raise RuntimeError("Failed to prepare Lambda assets for deployment")
        
        # Dictionary to store all Lambda functions
        self.lambda_functions: Dict[str, lambda_.Function] = {}
        
        # Create all Lambda functions
        self._create_main_oscar_agent()
        self._create_communication_handler()
        self._create_jenkins_agent()
        self._create_metrics_agents()
        
        # Add outputs for important resources
        self._add_outputs()
    
    def _create_main_oscar_agent(self) -> None:
        """
        Create the main OSCAR agent Lambda function with Slack event processing capabilities.
        """
        logger.info("Creating main OSCAR agent Lambda function")
        
        # Get the base Lambda execution role from permissions stack
        execution_role = self.permissions_stack.lambda_execution_roles["base"]
        
        # Grant access to central environment secret
        self.secrets_stack.grant_read_access(execution_role)
        
        function = lambda_.Function(
            self, "MainOscarAgent",
            function_name="oscar-supervisor-agent-cdk",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="app.lambda_handler",
            code=lambda_.Code.from_asset(get_lambda_asset_path("oscar-agent")),
            timeout=Duration.seconds(300),  # 5 minutes for complex agent interactions
            memory_size=1024,  # Higher memory for better performance
            environment=self._get_main_agent_environment_variables(),
            role=execution_role,
            description="Main OSCAR agent with Slack event processing capabilities",
            reserved_concurrent_executions=10  # Limit concurrent executions
        )
        
        self.lambda_functions["main_agent"] = function
        logger.info("Created main OSCAR agent Lambda function")
    
    def _create_communication_handler(self) -> None:
        """
        Create the communication handler Lambda function for Bedrock action groups.
        """
        logger.info("Creating communication handler Lambda function")
        
        # Get the communication handler execution role from permissions stack
        execution_role = self.permissions_stack.lambda_execution_roles["communication"]
        
        # Grant access to central environment secret
        self.secrets_stack.grant_read_access(execution_role)
        
        function = lambda_.Function(
            self, "CommunicationHandler",
            function_name="oscar-communication-handler-cdk",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",  # Flattened structure
            code=lambda_.Code.from_asset(get_lambda_asset_path("oscar-communication-handler")),  # Dynamically generated flattened asset
            timeout=Duration.seconds(60),
            memory_size=512,
            environment=self._get_communication_handler_environment_variables(),
            role=execution_role,
            description="Communication handler for OSCAR Bedrock action groups",
            reserved_concurrent_executions=20  # Higher concurrency for action groups
        )
        
        self.lambda_functions["communication_handler"] = function
        logger.info("Created communication handler Lambda function")
    
    def _create_jenkins_agent(self) -> None:
        """
        Create the Jenkins agent Lambda function for CI/CD integration.
        """
        logger.info("Creating Jenkins agent Lambda function")
        
        # Get the Jenkins execution role from permissions stack
        execution_role = self.permissions_stack.lambda_execution_roles["jenkins"]
        
        # Grant access to central environment secret
        self.secrets_stack.grant_read_access(execution_role)
        
        function = lambda_.Function(
            self, "JenkinsAgent",
            function_name="oscar-jenkins-agent-cdk",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(get_lambda_asset_path("jenkins")),
            timeout=Duration.seconds(120),  # 2 minutes for Jenkins API calls
            memory_size=512,
            environment=self._get_jenkins_agent_environment_variables(),
            role=execution_role,
            description="Jenkins agent for OSCAR CI/CD operations",
            reserved_concurrent_executions=5  # Limited concurrency for Jenkins operations
        )
        
        self.lambda_functions["jenkins_agent"] = function
        logger.info("Created Jenkins agent Lambda function")
    
    def _create_metrics_agents(self) -> None:
        """
        Create all metrics agent Lambda functions with VPC configuration.
        """
        logger.info("Creating metrics agent Lambda functions")
        
        # Get the VPC execution role from permissions stack (references existing authorized role)
        execution_role = self.permissions_stack.lambda_execution_roles["vpc"]
        
        # Grant access to central environment secret
        self.secrets_stack.grant_read_access(execution_role)
        
        # Get VPC configuration for metrics agents (they need VPC access for OpenSearch)
        vpc_id = os.environ.get("VPC_ID")
        subnet_ids = os.environ.get("SUBNET_IDS", "").split(",") if os.environ.get("SUBNET_IDS") else []
        security_group_id = os.environ.get("SECURITY_GROUP_ID")
        
        vpc = None
        vpc_subnets = None
        security_groups = None
        
        if vpc_id and subnet_ids:
            # Import existing VPC and subnets
            vpc = ec2.Vpc.from_lookup(self, "ExistingVpc", vpc_id=vpc_id)
            
            # Import existing subnets
            subnets = []
            for i, subnet_id in enumerate(subnet_ids):
                if subnet_id.strip():
                    subnet = ec2.Subnet.from_subnet_id(self, f"ExistingSubnet{i}", subnet_id.strip())
                    subnets.append(subnet)
            
            if subnets:
                vpc_subnets = ec2.SubnetSelection(subnets=subnets)
            
            # Import existing security group if provided
            if security_group_id:
                security_group = ec2.SecurityGroup.from_security_group_id(
                    self, "ExistingSecurityGroup", security_group_id
                )
                security_groups = [security_group]
            
            logger.info(f"Using VPC {vpc_id} with {len(subnets)} subnets for metrics Lambda functions")
        
        # Create separate metrics agents for each type
        metrics_types = [
            ("build", "Build metrics analysis and reporting"),
            ("test", "Test metrics analysis and reporting"), 
            ("release", "Release metrics analysis and reporting")
        ]
        
        for metrics_type, description in metrics_types:
            function = lambda_.Function(
                self, f"{metrics_type.title()}MetricsAgent",
                function_name=f"oscar-{metrics_type}-metrics-agent-cdk",
                runtime=lambda_.Runtime.PYTHON_3_12,
                handler="lambda_function.lambda_handler",
                code=lambda_.Code.from_asset(get_lambda_asset_path("metrics")),
                timeout=Duration.seconds(180),  # 3 minutes for metrics queries
                memory_size=1024,  # Higher memory for data processing
                environment=self._get_metrics_agent_environment_variables(metrics_type),
                role=execution_role,
                description=f"OSCAR {description} (VPC-enabled)",
                reserved_concurrent_executions=5,  # Limited concurrency for metrics
                vpc=vpc,
                vpc_subnets=vpc_subnets,
                security_groups=security_groups,
                allow_public_subnet=True  # Allow placement in public subnets when no private subnets available
            )
            
            self.lambda_functions[f"{metrics_type}_metrics"] = function
            logger.info(f"Created {metrics_type} metrics agent Lambda function")
        
        logger.info("Created all metrics agent Lambda functions")
    
    def _get_main_agent_environment_variables(self) -> Dict[str, str]:
        """
        Get environment variables for the main OSCAR agent Lambda function.
        
        Returns:
            Dictionary of environment variables for the main agent
        """
        return {
            # Central secret reference - Lambda will load from Secrets Manager at runtime
            "CENTRAL_SECRET_NAME": self.secrets_stack.central_env_secret.secret_name,
            
            # DynamoDB table names with CDK suffix (use base names to avoid duplication)
            "SESSIONS_TABLE_NAME": f"oscar-agent-sessions-{os.environ.get('ENVIRONMENT', 'dev')}-cdk",
            "CONTEXT_TABLE_NAME": f"oscar-agent-context-{os.environ.get('ENVIRONMENT', 'dev')}-cdk",
            
            # TTL configurations from .env
            "DEDUP_TTL": os.environ.get("DEDUP_TTL", "300"),
            "SESSION_TTL": os.environ.get("SESSION_TTL", "3600"),
            "CONTEXT_TTL": os.environ.get("CONTEXT_TTL", "604800"),  # 7 days
            
            # Context management from .env
            "MAX_CONTEXT_LENGTH": os.environ.get("MAX_CONTEXT_LENGTH", "3000"),
            "CONTEXT_SUMMARY_LENGTH": os.environ.get("CONTEXT_SUMMARY_LENGTH", "500"),
            
            # Feature flags from .env
            "ENABLE_DM": os.environ.get("ENABLE_DM", "false"),
            
            # AWS configuration from .env (AWS_REGION is automatically set by Lambda runtime)
            "AWS_ACCOUNT_ID": os.environ.get("AWS_ACCOUNT_ID") or os.environ.get("CDK_DEFAULT_ACCOUNT", ""),
            
            # Logging from .env
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO")
        }
    
    def _get_communication_handler_environment_variables(self) -> Dict[str, str]:
        """
        Get environment variables for the communication handler Lambda function.
        
        Returns:
            Dictionary of environment variables for the communication handler
        """
        return {
            # Central secret reference
            "CENTRAL_SECRET_NAME": self.secrets_stack.central_env_secret.secret_name,
            
            # DynamoDB table names with CDK suffix (use base names to avoid duplication)
            "SESSIONS_TABLE_NAME": f"oscar-agent-sessions-{os.environ.get('ENVIRONMENT', 'dev')}-cdk",
            "CONTEXT_TABLE_NAME": f"oscar-agent-context-{os.environ.get('ENVIRONMENT', 'dev')}-cdk",
            
            # Communication settings
            "MESSAGE_TIMEOUT": os.environ.get("MESSAGE_TIMEOUT", "30"),
            "MAX_RETRIES": os.environ.get("MAX_RETRIES", "3"),
            
            # Logging
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO")
        }
    
    def _get_jenkins_agent_environment_variables(self) -> Dict[str, str]:
        """
        Get environment variables for the Jenkins agent Lambda function.
        
        Returns:
            Dictionary of environment variables for the Jenkins agent
        """
        return {
            # Central secret reference
            "CENTRAL_SECRET_NAME": self.secrets_stack.central_env_secret.secret_name,
            
            # Jenkins configuration
            "JENKINS_TIMEOUT": os.environ.get("JENKINS_TIMEOUT", "60"),
            "MAX_BUILD_WAIT_TIME": os.environ.get("MAX_BUILD_WAIT_TIME", "1800"),  # 30 minutes
            
            # Logging
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO")
        }
    
    def _get_metrics_agent_environment_variables(self, metrics_type: str = "unified") -> Dict[str, str]:
        """
        Get environment variables for metrics agent Lambda function.
        
        Args:
            metrics_type: Type of metrics agent (build, test, release, or unified)
            
        Returns:
            Dictionary of environment variables for the metrics agent
        """
        return {
            # Central secret reference
            "CENTRAL_SECRET_NAME": self.secrets_stack.central_env_secret.secret_name,
            
            # Metrics configuration from .env - specify the type
            "METRICS_TYPE": metrics_type,
            "REQUEST_TIMEOUT": os.environ.get("REQUEST_TIMEOUT", "30"),
            "MAX_RESULTS": os.environ.get("MAX_RESULTS", "500"),
            
            # OpenSearch configuration from .env
            "OPENSEARCH_HOST": os.environ.get("OPENSEARCH_HOST", "https://aos-a4f4c9d2accb-brkjnnuiccoheln4bmcpzv4auq.us-east-1.es.amazonaws.com"),
            "OPENSEARCH_DOMAIN_ACCOUNT": os.environ.get("OPENSEARCH_DOMAIN_ACCOUNT", "979020455945"),
            "OPENSEARCH_REGION": os.environ.get("OPENSEARCH_REGION", "us-east-1"),
            
            # Cross-account access from .env
            "METRICS_CROSS_ACCOUNT_ROLE_ARN": os.environ.get("METRICS_CROSS_ACCOUNT_ROLE_ARN", "arn:aws:iam::979020455945:role/OpenSearchOscarAccessRole"),
            "EXTERNAL_ID": "oscar-metrics-access",
            
            # VPC configuration from .env
            "VPC_ID": os.environ.get("VPC_ID", "vpc-0f2061a1321c2d669"),
            "SUBNET_IDS": os.environ.get("SUBNET_IDS", "subnet-050b451b74a9e942e,subnet-0689046ab78f4f94d,subnet-04bc37db52fc9603a,subnet-045e091dc5573bd1b,subnet-06b2bf5e225458fd6,subnet-0bfe69389ea34bab3"),
            "SECURITY_GROUP_ID": os.environ.get("SECURITY_GROUP_ID", "sg-0e18a7fad124327c5"),
            
            # Logging from .env
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO")
        }
    
    def update_function_code(self, function_name: str, code_path: str) -> bool:
        """
        Update Lambda function code without changing permissions or configurations.
        
        Args:
            function_name: Name of the function to update
            code_path: Path to the new code
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Find the function in our managed functions
            function_key = None
            for key, func in self.lambda_functions.items():
                if func.function_name == function_name:
                    function_key = key
                    break
            
            if not function_key:
                logger.error(f"Function {function_name} not found in managed functions")
                return False
            
            # Update the function code
            # Note: In CDK, code updates happen during deployment
            # This method provides the interface for code-only updates
            logger.info(f"Code update requested for {function_name} with code from {code_path}")
            
            # Validate that the code path exists
            if not os.path.exists(code_path):
                logger.error(f"Code path {code_path} does not exist")
                return False
            
            logger.info(f"Code update validated for {function_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update function code for {function_name}: {e}")
            return False
    
    def get_function_environment(self, function_name: str) -> Dict[str, str]:
        """
        Get environment variables for a specific Lambda function.
        
        Args:
            function_name: Name of the function
            
        Returns:
            Dictionary of environment variables
        """
        # Find the function and return its environment variables
        for key, func in self.lambda_functions.items():
            if func.function_name == function_name:
                # Return the environment variables based on function type
                if "main_agent" in key:
                    return self._get_main_agent_environment_variables()
                elif "communication_handler" in key:
                    return self._get_communication_handler_environment_variables()
                elif "jenkins_agent" in key:
                    return self._get_jenkins_agent_environment_variables()
                elif "metrics" in key:
                    return self._get_metrics_agent_environment_variables()
        
        logger.warning(f"Function {function_name} not found")
        return {}
    
    def _add_outputs(self) -> None:
        """
        Add CloudFormation outputs for all Lambda functions.
        """
        # Output for each Lambda function
        for function_key, function in self.lambda_functions.items():
            # Function name output
            CfnOutput(
                self, f"{function_key.title().replace('_', '')}FunctionName",
                value=function.function_name,
                description=f"Name of the {function_key.replace('_', ' ')} Lambda function",
                export_name=f"Oscar{function_key.title().replace('_', '')}FunctionName"
            )
            
            # Function ARN output
            CfnOutput(
                self, f"{function_key.title().replace('_', '')}FunctionArn",
                value=function.function_arn,
                description=f"ARN of the {function_key.replace('_', ' ')} Lambda function",
                export_name=f"Oscar{function_key.title().replace('_', '')}FunctionArn"
            )
        
        # Summary output
        function_names = [func.function_name for func in self.lambda_functions.values()]
        CfnOutput(
            self, "AllLambdaFunctions",
            value=",".join(function_names),
            description="Comma-separated list of all OSCAR Lambda function names"
        )
    
    @property
    def lambda_functions_dict(self) -> Dict[str, lambda_.Function]:
        """
        Get dictionary of all Lambda functions.
        
        Returns:
            Dictionary mapping function keys to Lambda function objects
        """
        return self.lambda_functions.copy()
    
    def get_function_by_name(self, function_name: str) -> Optional[lambda_.Function]:
        """
        Get Lambda function by name.
        
        Args:
            function_name: Name of the function to retrieve
            
        Returns:
            Lambda function object or None if not found
        """
        for func in self.lambda_functions.values():
            if func.function_name == function_name:
                return func
        return None