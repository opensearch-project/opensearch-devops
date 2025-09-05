"""
Agent configuration validation utilities for validating Bedrock agent configurations.
Implements validation functions for agent configuration completeness, schema validation
for action groups and knowledge base associations, and validation for foundation model
configurations and collaborator settings.
"""

import json
import re
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from agent_config_builder import (
    AgentConfig, ActionGroupConfig, KnowledgeBaseConfig, 
    CollaboratorConfig, GuardrailConfig, FoundationModel
)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: ValidationSeverity
    message: str
    field_path: str = ""
    suggestion: str = ""
    
    def __str__(self) -> str:
        prefix = {
            ValidationSeverity.ERROR: "✗ ERROR",
            ValidationSeverity.WARNING: "⚠ WARNING", 
            ValidationSeverity.INFO: "ℹ INFO"
        }[self.severity]
        
        result = f"{prefix}: {self.message}"
        if self.field_path:
            result += f" (Field: {self.field_path})"
        if self.suggestion:
            result += f" - Suggestion: {self.suggestion}"
        return result


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    issues: List[ValidationIssue]
    
    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return len(self.errors) > 0
    
    def add_issue(self, severity: ValidationSeverity, message: str, field_path: str = "", suggestion: str = ""):
        """Add a validation issue."""
        self.issues.append(ValidationIssue(severity, message, field_path, suggestion))
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False


class AgentConfigValidator:
    """Validator for Bedrock agent configurations."""
    
    # Valid AWS ARN patterns
    LAMBDA_ARN_PATTERN = re.compile(r'^arn:aws:lambda:[a-z0-9-]+:\d{12}:function:[a-zA-Z0-9-_]+$')
    IAM_ROLE_ARN_PATTERN = re.compile(r'^arn:aws:iam::\d{12}:role/[a-zA-Z0-9-_/]+$')
    BEDROCK_AGENT_ARN_PATTERN = re.compile(r'^arn:aws:bedrock:[a-z0-9-]+:\d{12}:agent/[A-Z0-9]+$')
    
    # Valid agent ID patterns
    AGENT_ID_PATTERN = re.compile(r'^[A-Z0-9]{10}$')
    ALIAS_ID_PATTERN = re.compile(r'^[A-Z0-9]{10}$')
    KNOWLEDGE_BASE_ID_PATTERN = re.compile(r'^[A-Z0-9]{10}$')
    
    # Valid foundation models (including inference profiles)
    VALID_FOUNDATION_MODELS = {model.value for model in FoundationModel}
    
    # Valid inference profile patterns
    INFERENCE_PROFILE_PATTERN = re.compile(r'^arn:aws:bedrock:[a-z0-9-]+:\d{12}:inference-profile/[a-zA-Z0-9.-]+$')
    
    # Required Bedrock action group schema fields
    REQUIRED_ACTION_GROUP_SCHEMA_FIELDS = ['openAPIVersion', 'info', 'paths']
    
    def __init__(self):
        """Initialize the validator."""
        pass
    
    def validate_agent_config(self, agent_config: AgentConfig) -> ValidationResult:
        """
        Validate complete agent configuration.
        
        Args:
            agent_config: AgentConfig object to validate
            
        Returns:
            ValidationResult with all validation issues
        """
        result = ValidationResult(is_valid=True, issues=[])
        
        # Validate basic agent properties
        self._validate_basic_properties(agent_config, result)
        
        # Validate foundation model
        self._validate_foundation_model(agent_config, result)
        
        # Validate agent and alias IDs
        self._validate_agent_ids(agent_config, result)
        
        # Validate action groups
        self._validate_action_groups(agent_config.action_groups, result)
        
        # Validate knowledge bases
        self._validate_knowledge_bases(agent_config.knowledge_bases, result)
        
        # Validate collaborators
        self._validate_collaborators(agent_config.collaborators, result)
        
        # Validate guardrails
        if agent_config.guardrails:
            self._validate_guardrails(agent_config.guardrails, result)
        
        # Validate IAM role ARN
        if agent_config.agent_resource_role_arn:
            self._validate_iam_role_arn(agent_config.agent_resource_role_arn, result, "agent_resource_role_arn")
        
        # Validate session TTL
        self._validate_session_ttl(agent_config.idle_session_ttl_in_seconds, result)
        
        # Validate tags
        self._validate_tags(agent_config.tags, result)
        
        return result
    
    def _validate_basic_properties(self, agent_config: AgentConfig, result: ValidationResult):
        """Validate basic required properties."""
        if not agent_config.agent_name:
            result.add_issue(ValidationSeverity.ERROR, "Agent name is required", "agent_name")
        elif len(agent_config.agent_name) > 100:
            result.add_issue(ValidationSeverity.ERROR, "Agent name must be 100 characters or less", "agent_name")
        elif not re.match(r'^[a-zA-Z0-9-_]+$', agent_config.agent_name):
            result.add_issue(ValidationSeverity.WARNING, "Agent name should only contain alphanumeric characters, hyphens, and underscores", "agent_name")
        
        if not agent_config.description:
            result.add_issue(ValidationSeverity.ERROR, "Agent description is required", "description")
        elif len(agent_config.description) > 500:
            result.add_issue(ValidationSeverity.ERROR, "Agent description must be 500 characters or less", "description")
        
        if not agent_config.instructions:
            result.add_issue(ValidationSeverity.ERROR, "Agent instructions are required", "instructions")
        elif len(agent_config.instructions) > 4000:
            result.add_issue(ValidationSeverity.WARNING, f"Agent instructions are long ({len(agent_config.instructions)} chars, max recommended: 4000)", "instructions", "Consider shortening instructions for better performance")
    
    def _validate_foundation_model(self, agent_config: AgentConfig, result: ValidationResult):
        """Validate foundation model configuration."""
        if not agent_config.foundation_model:
            result.add_issue(ValidationSeverity.ERROR, "Foundation model is required", "foundation_model")
        elif (agent_config.foundation_model not in self.VALID_FOUNDATION_MODELS and 
              not self.INFERENCE_PROFILE_PATTERN.match(agent_config.foundation_model)):
            valid_models = ", ".join(self.VALID_FOUNDATION_MODELS)
            result.add_issue(
                ValidationSeverity.WARNING, 
                f"Non-standard foundation model (inference profile): {agent_config.foundation_model}", 
                "foundation_model",
                f"Standard models: {valid_models}"
            )
    
    def _validate_agent_ids(self, agent_config: AgentConfig, result: ValidationResult):
        """Validate agent and alias IDs."""
        if agent_config.agent_id:
            if not self.AGENT_ID_PATTERN.match(agent_config.agent_id):
                result.add_issue(
                    ValidationSeverity.ERROR, 
                    f"Invalid agent ID format: {agent_config.agent_id}", 
                    "agent_id",
                    "Agent ID should be 10 uppercase alphanumeric characters"
                )
        
        if agent_config.primary_alias_id:
            if not self.ALIAS_ID_PATTERN.match(agent_config.primary_alias_id):
                result.add_issue(
                    ValidationSeverity.ERROR, 
                    f"Invalid alias ID format: {agent_config.primary_alias_id}", 
                    "primary_alias_id",
                    "Alias ID should be 10 uppercase alphanumeric characters"
                )
    
    def _validate_action_groups(self, action_groups: List[ActionGroupConfig], result: ValidationResult):
        """Validate action group configurations."""
        if not action_groups:
            result.add_issue(ValidationSeverity.WARNING, "No action groups configured", "action_groups", "Consider adding action groups for agent functionality")
            return
        
        action_group_names = set()
        
        for i, action_group in enumerate(action_groups):
            field_prefix = f"action_groups[{i}]"
            
            # Validate name
            if not action_group.name:
                result.add_issue(ValidationSeverity.ERROR, "Action group name is required", f"{field_prefix}.name")
            elif action_group.name in action_group_names:
                result.add_issue(ValidationSeverity.ERROR, f"Duplicate action group name: {action_group.name}", f"{field_prefix}.name")
            else:
                action_group_names.add(action_group.name)
            
            # Validate description
            if not action_group.description:
                result.add_issue(ValidationSeverity.WARNING, "Action group description is recommended", f"{field_prefix}.description")
            
            # Validate Lambda function ARN
            if not action_group.lambda_function_arn:
                result.add_issue(ValidationSeverity.ERROR, "Lambda function ARN is required", f"{field_prefix}.lambda_function_arn")
            elif not self.LAMBDA_ARN_PATTERN.match(action_group.lambda_function_arn):
                result.add_issue(
                    ValidationSeverity.ERROR, 
                    f"Invalid Lambda function ARN format: {action_group.lambda_function_arn}", 
                    f"{field_prefix}.lambda_function_arn"
                )
            
            # Validate API schema
            if not action_group.api_schema:
                result.add_issue(ValidationSeverity.WARNING, "Action group schema is empty (may be extracted from Bedrock)", f"{field_prefix}.api_schema")
            else:
                self._validate_bedrock_action_group_schema(action_group.api_schema, result, f"{field_prefix}.api_schema")
            
            # Validate execution role ARN if provided
            if action_group.execution_role_arn:
                self._validate_iam_role_arn(action_group.execution_role_arn, result, f"{field_prefix}.execution_role_arn")
            
            # Validate action group state
            if action_group.action_group_state not in ['ENABLED', 'DISABLED']:
                result.add_issue(
                    ValidationSeverity.ERROR, 
                    f"Invalid action group state: {action_group.action_group_state}", 
                    f"{field_prefix}.action_group_state",
                    "Must be 'ENABLED' or 'DISABLED'"
                )
    
    def _validate_bedrock_action_group_schema(self, schema: Dict[str, Any], result: ValidationResult, field_path: str):
        """Validate Bedrock action group schema structure."""
        if not isinstance(schema, dict):
            result.add_issue(ValidationSeverity.ERROR, "Action group schema must be a dictionary", field_path)
            return
        
        # Check required fields for Bedrock action group schema
        for required_field in self.REQUIRED_ACTION_GROUP_SCHEMA_FIELDS:
            if required_field not in schema:
                result.add_issue(
                    ValidationSeverity.ERROR, 
                    f"Missing required action group schema field: {required_field}", 
                    f"{field_path}.{required_field}"
                )
        
        # Validate OpenAPI version (Bedrock supports OpenAPI 3.x)
        if 'openAPIVersion' in schema:
            version = schema['openAPIVersion']
            if not isinstance(version, str) or not version.startswith('3.'):
                result.add_issue(
                    ValidationSeverity.WARNING, 
                    f"Unsupported OpenAPI version for Bedrock: {version}", 
                    f"{field_path}.openAPIVersion",
                    "Bedrock action groups require OpenAPI 3.x"
                )
        
        # Validate info section
        if 'info' in schema:
            info = schema['info']
            if not isinstance(info, dict):
                result.add_issue(ValidationSeverity.ERROR, "Action group schema info must be a dictionary", f"{field_path}.info")
            else:
                if 'title' not in info:
                    result.add_issue(ValidationSeverity.ERROR, "Action group schema info.title is required", f"{field_path}.info.title")
                if 'version' not in info:
                    result.add_issue(ValidationSeverity.ERROR, "Action group schema info.version is required", f"{field_path}.info.version")
        
        # Validate paths section (Bedrock action group specific validation)
        if 'paths' in schema:
            paths = schema['paths']
            if not isinstance(paths, dict):
                result.add_issue(ValidationSeverity.ERROR, "Action group schema paths must be a dictionary", f"{field_path}.paths")
            elif not paths:
                result.add_issue(ValidationSeverity.WARNING, "No action group paths defined", f"{field_path}.paths")
            else:
                # Validate each path for Bedrock-specific requirements
                for path_name, path_config in paths.items():
                    if not isinstance(path_config, dict):
                        continue
                    
                    # Check for HTTP methods
                    http_methods = ['get', 'post', 'put', 'delete', 'patch']
                    has_method = any(method in path_config for method in http_methods)
                    
                    if not has_method:
                        result.add_issue(
                            ValidationSeverity.WARNING,
                            f"Path {path_name} has no HTTP methods defined",
                            f"{field_path}.paths.{path_name}"
                        )
    
    def _validate_knowledge_bases(self, knowledge_bases: List[KnowledgeBaseConfig], result: ValidationResult):
        """Validate knowledge base configurations."""
        if not knowledge_bases:
            result.add_issue(ValidationSeverity.INFO, "No knowledge bases configured", "knowledge_bases")
            return
        
        kb_ids = set()
        
        for i, kb in enumerate(knowledge_bases):
            field_prefix = f"knowledge_bases[{i}]"
            
            # Validate knowledge base ID
            if not kb.knowledge_base_id:
                result.add_issue(ValidationSeverity.ERROR, "Knowledge base ID is required", f"{field_prefix}.knowledge_base_id")
            elif kb.knowledge_base_id in kb_ids:
                result.add_issue(ValidationSeverity.ERROR, f"Duplicate knowledge base ID: {kb.knowledge_base_id}", f"{field_prefix}.knowledge_base_id")
            elif not self.KNOWLEDGE_BASE_ID_PATTERN.match(kb.knowledge_base_id):
                result.add_issue(
                    ValidationSeverity.ERROR, 
                    f"Invalid knowledge base ID format: {kb.knowledge_base_id}", 
                    f"{field_prefix}.knowledge_base_id",
                    "Knowledge base ID should be 10 uppercase alphanumeric characters"
                )
            else:
                kb_ids.add(kb.knowledge_base_id)
            
            # Validate knowledge base state
            if kb.knowledge_base_state not in ['ENABLED', 'DISABLED']:
                result.add_issue(
                    ValidationSeverity.ERROR, 
                    f"Invalid knowledge base state: {kb.knowledge_base_state}", 
                    f"{field_prefix}.knowledge_base_state",
                    "Must be 'ENABLED' or 'DISABLED'"
                )
            
            # Validate retrieval configuration
            if kb.retrieval_configuration:
                self._validate_retrieval_configuration(kb.retrieval_configuration, result, f"{field_prefix}.retrieval_configuration")
    
    def _validate_retrieval_configuration(self, config: Dict[str, Any], result: ValidationResult, field_path: str):
        """Validate knowledge base retrieval configuration."""
        if 'vectorSearchConfiguration' in config:
            vector_config = config['vectorSearchConfiguration']
            
            if 'numberOfResults' in vector_config:
                num_results = vector_config['numberOfResults']
                if not isinstance(num_results, int) or num_results < 1 or num_results > 100:
                    result.add_issue(
                        ValidationSeverity.ERROR, 
                        f"numberOfResults must be an integer between 1 and 100: {num_results}", 
                        f"{field_path}.vectorSearchConfiguration.numberOfResults"
                    )
            
            if 'overrideSearchType' in vector_config:
                search_type = vector_config['overrideSearchType']
                if search_type not in ['HYBRID', 'SEMANTIC']:
                    result.add_issue(
                        ValidationSeverity.ERROR, 
                        f"Invalid search type: {search_type}", 
                        f"{field_path}.vectorSearchConfiguration.overrideSearchType",
                        "Must be 'HYBRID' or 'SEMANTIC'"
                    )
    
    def _validate_collaborators(self, collaborators: List[CollaboratorConfig], result: ValidationResult):
        """Validate collaborator configurations."""
        if not collaborators:
            return  # Collaborators are optional
        
        collaborator_ids = set()
        
        for i, collaborator in enumerate(collaborators):
            field_prefix = f"collaborators[{i}]"
            
            # Validate agent ID
            if not collaborator.agent_id:
                result.add_issue(ValidationSeverity.ERROR, "Collaborator agent ID is required", f"{field_prefix}.agent_id")
            elif collaborator.agent_id in collaborator_ids:
                result.add_issue(ValidationSeverity.ERROR, f"Duplicate collaborator agent ID: {collaborator.agent_id}", f"{field_prefix}.agent_id")
            elif not self.AGENT_ID_PATTERN.match(collaborator.agent_id):
                result.add_issue(
                    ValidationSeverity.ERROR, 
                    f"Invalid collaborator agent ID format: {collaborator.agent_id}", 
                    f"{field_prefix}.agent_id"
                )
            else:
                collaborator_ids.add(collaborator.agent_id)
            
            # Validate agent version
            if not collaborator.agent_version:
                result.add_issue(ValidationSeverity.ERROR, "Collaborator agent version is required", f"{field_prefix}.agent_version")
            
            # Validate collaboration role
            if not collaborator.collaboration_role:
                result.add_issue(ValidationSeverity.ERROR, "Collaboration role is required", f"{field_prefix}.collaboration_role")
            
            # Validate relay conversation history
            if collaborator.relay_conversation_history not in ['TO_COLLABORATOR', 'DISABLED']:
                result.add_issue(
                    ValidationSeverity.ERROR, 
                    f"Invalid relay conversation history: {collaborator.relay_conversation_history}", 
                    f"{field_prefix}.relay_conversation_history",
                    "Must be 'TO_COLLABORATOR' or 'DISABLED'"
                )
    
    def _validate_guardrails(self, guardrails: GuardrailConfig, result: ValidationResult):
        """Validate guardrail configuration."""
        if not guardrails.guardrail_identifier:
            result.add_issue(ValidationSeverity.ERROR, "Guardrail identifier is required", "guardrails.guardrail_identifier")
        
        if not guardrails.guardrail_version:
            result.add_issue(ValidationSeverity.ERROR, "Guardrail version is required", "guardrails.guardrail_version")
    
    def _validate_iam_role_arn(self, role_arn: str, result: ValidationResult, field_path: str):
        """Validate IAM role ARN format."""
        if not self.IAM_ROLE_ARN_PATTERN.match(role_arn):
            result.add_issue(
                ValidationSeverity.ERROR, 
                f"Invalid IAM role ARN format: {role_arn}", 
                field_path,
                "ARN should match pattern: arn:aws:iam::ACCOUNT:role/ROLE_NAME"
            )
    
    def _validate_session_ttl(self, ttl: int, result: ValidationResult):
        """Validate session TTL value."""
        if ttl < 60 or ttl > 3600:
            result.add_issue(
                ValidationSeverity.WARNING, 
                f"Session TTL should be between 60 and 3600 seconds: {ttl}", 
                "idle_session_ttl_in_seconds",
                "Recommended range: 300-1800 seconds"
            )
    
    def _validate_tags(self, tags: Dict[str, str], result: ValidationResult):
        """Validate tags configuration."""
        if not tags:
            result.add_issue(ValidationSeverity.INFO, "No tags configured", "tags", "Consider adding tags for resource management")
            return
        
        if len(tags) > 50:
            result.add_issue(ValidationSeverity.ERROR, f"Too many tags: {len(tags)}", "tags", "Maximum 50 tags allowed")
        
        for key, value in tags.items():
            if len(key) > 128:
                result.add_issue(ValidationSeverity.ERROR, f"Tag key too long: {key}", f"tags.{key}", "Maximum 128 characters")
            if len(value) > 256:
                result.add_issue(ValidationSeverity.ERROR, f"Tag value too long: {value}", f"tags.{key}", "Maximum 256 characters")
    
    def validate_config_file(self, config_file_path: str) -> ValidationResult:
        """
        Validate agent configuration from JSON file.
        
        Args:
            config_file_path: Path to the configuration JSON file
            
        Returns:
            ValidationResult with validation issues
        """
        result = ValidationResult(is_valid=True, issues=[])
        
        config_path = Path(config_file_path)
        if not config_path.exists():
            result.add_issue(ValidationSeverity.ERROR, f"Configuration file not found: {config_file_path}")
            return result
        
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            result.add_issue(ValidationSeverity.ERROR, f"Invalid JSON in configuration file: {e}")
            return result
        except Exception as e:
            result.add_issue(ValidationSeverity.ERROR, f"Error reading configuration file: {e}")
            return result
        
        # Convert to AgentConfig object and validate
        try:
            from agent_config_builder import AgentConfigBuilder
            builder = AgentConfigBuilder()
            agent_config = builder._build_agent_config(config_data)
            return self.validate_agent_config(agent_config)
        except Exception as e:
            result.add_issue(ValidationSeverity.ERROR, f"Error building agent configuration: {e}")
            return result
    
    def validate_multiple_configs(self, config_files: List[str]) -> Dict[str, ValidationResult]:
        """
        Validate multiple agent configuration files.
        
        Args:
            config_files: List of configuration file paths
            
        Returns:
            Dictionary mapping file path to ValidationResult
        """
        results = {}
        
        for config_file in config_files:
            results[config_file] = self.validate_config_file(config_file)
        
        return results
    
    def generate_validation_report(self, results: Union[ValidationResult, Dict[str, ValidationResult]]) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            results: ValidationResult or dictionary of results
            
        Returns:
            Formatted validation report string
        """
        if isinstance(results, ValidationResult):
            return self._format_single_result("Configuration", results)
        
        report_lines = ["Agent Configuration Validation Report", "=" * 50, ""]
        
        total_configs = len(results)
        valid_configs = sum(1 for result in results.values() if result.is_valid)
        
        report_lines.append(f"Summary: {valid_configs}/{total_configs} configurations valid")
        report_lines.append("")
        
        for config_file, result in results.items():
            report_lines.append(self._format_single_result(config_file, result))
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def _format_single_result(self, name: str, result: ValidationResult) -> str:
        """Format a single validation result."""
        lines = [f"{name}: {'✓ VALID' if result.is_valid else '✗ INVALID'}"]
        
        if result.issues:
            lines.append("-" * 40)
            for issue in result.issues:
                lines.append(str(issue))
        
        return "\n".join(lines)


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate Bedrock agent configurations')
    parser.add_argument('config_files', nargs='+', help='Configuration files to validate')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    
    args = parser.parse_args()
    
    validator = AgentConfigValidator()
    results = validator.validate_multiple_configs(args.config_files)
    
    if args.report:
        print(validator.generate_validation_report(results))
    else:
        # Simple summary
        for config_file, result in results.items():
            status = "✓ VALID" if result.is_valid else "✗ INVALID"
            print(f"{config_file}: {status}")
            if result.has_errors:
                for error in result.errors:
                    print(f"  {error}")


if __name__ == "__main__":
    main()