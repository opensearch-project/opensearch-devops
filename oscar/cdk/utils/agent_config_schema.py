"""
JSON Schema definitions for Bedrock agent configurations.
Provides schema validation capabilities for agent configurations, action groups,
knowledge base associations, and collaborator settings.
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

# JSON Schema for Bedrock Action Group specification
BEDROCK_ACTION_GROUP_SCHEMA = {
    "type": "object",
    "required": ["openAPIVersion", "info", "paths"],
    "properties": {
        "openAPIVersion": {
            "type": "string",
            "pattern": "^3\\."
        },
        "info": {
            "type": "object",
            "required": ["title", "version"],
            "properties": {
                "title": {"type": "string"},
                "version": {"type": "string"},
                "description": {"type": "string"}
            }
        },
        "paths": {
            "type": "object",
            "patternProperties": {
                "^/": {
                    "type": "object",
                    "patternProperties": {
                        "^(get|post|put|delete|patch|head|options|trace)$": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "parameters": {
                                    "type": "object",
                                    "patternProperties": {
                                        "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                                            "type": "object",
                                            "properties": {
                                                "type": {"type": "string"},
                                                "description": {"type": "string"},
                                                "required": {"type": "boolean"}
                                            }
                                        }
                                    }
                                },
                                "requestBody": {"type": "object"},
                                "responses": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    }
}

# JSON Schema for Action Group configuration
ACTION_GROUP_SCHEMA = {
    "type": "object",
    "required": ["name", "description", "lambda_function_arn", "api_schema"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9-_]+$"
        },
        "description": {
            "type": "string",
            "minLength": 1,
            "maxLength": 500
        },
        "lambda_function_arn": {
            "type": "string",
            "pattern": "^arn:aws:lambda:[a-z0-9-]+:\\d{12}:function:[a-zA-Z0-9-_]+$"
        },
        "api_schema": BEDROCK_ACTION_GROUP_SCHEMA,
        "execution_role_arn": {
            "type": "string",
            "pattern": "^arn:aws:iam::\\d{12}:role/[a-zA-Z0-9-_/]+$"
        },
        "action_group_state": {
            "type": "string",
            "enum": ["ENABLED", "DISABLED"]
        }
    }
}

# JSON Schema for Knowledge Base configuration
KNOWLEDGE_BASE_SCHEMA = {
    "type": "object",
    "required": ["knowledge_base_id"],
    "properties": {
        "knowledge_base_id": {
            "type": "string",
            "pattern": "^[A-Z0-9]{10}$"
        },
        "knowledge_base_state": {
            "type": "string",
            "enum": ["ENABLED", "DISABLED"]
        },
        "description": {
            "type": "string",
            "maxLength": 500
        },
        "retrieval_configuration": {
            "type": "object",
            "properties": {
                "vectorSearchConfiguration": {
                    "type": "object",
                    "properties": {
                        "numberOfResults": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "overrideSearchType": {
                            "type": "string",
                            "enum": ["HYBRID", "SEMANTIC"]
                        }
                    }
                }
            }
        }
    }
}

# JSON Schema for Collaborator configuration
COLLABORATOR_SCHEMA = {
    "type": "object",
    "required": ["agent_id", "agent_version", "collaboration_role"],
    "properties": {
        "agent_id": {
            "type": "string",
            "pattern": "^[A-Z0-9]{10}$"
        },
        "agent_version": {
            "type": "string",
            "minLength": 1
        },
        "collaboration_role": {
            "type": "string",
            "minLength": 1
        },
        "relay_conversation_history": {
            "type": "string",
            "enum": ["TO_COLLABORATOR", "DISABLED"]
        }
    }
}

# JSON Schema for Guardrail configuration
GUARDRAIL_SCHEMA = {
    "type": "object",
    "required": ["guardrail_identifier", "guardrail_version"],
    "properties": {
        "guardrail_identifier": {
            "type": "string",
            "minLength": 1
        },
        "guardrail_version": {
            "type": "string",
            "minLength": 1
        }
    }
}

# JSON Schema for complete Agent configuration
AGENT_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Bedrock Agent Configuration",
    "description": "Schema for validating Bedrock agent configurations",
    "type": "object",
    "required": ["agent_name", "description", "instructions", "foundation_model"],
    "properties": {
        "agent_name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9-_]+$"
        },
        "description": {
            "type": "string",
            "minLength": 1,
            "maxLength": 500
        },
        "instructions": {
            "type": "string",
            "minLength": 1,
            "maxLength": 4000
        },
        "foundation_model": {
            "type": "string",
            "enum": [
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "anthropic.claude-3-5-haiku-20241022-v1:0",
                "anthropic.claude-3-sonnet-20240229-v1:0",
                "anthropic.claude-3-haiku-20240307-v1:0"
            ]
        },
        "agent_id": {
            "type": "string",
            "pattern": "^[A-Z0-9]{10}$"
        },
        "primary_alias_id": {
            "type": "string",
            "pattern": "^[A-Z0-9]{10}$"
        },
        "idle_session_ttl_in_seconds": {
            "type": "integer",
            "minimum": 60,
            "maximum": 3600
        },
        "agent_resource_role_arn": {
            "type": "string",
            "pattern": "^arn:aws:iam::\\d{12}:role/[a-zA-Z0-9-_/]+$"
        },
        "customer_encryption_key_arn": {
            "type": "string",
            "pattern": "^arn:aws:kms:[a-z0-9-]+:\\d{12}:key/[a-f0-9-]+$"
        },
        "action_groups": {
            "type": "array",
            "items": ACTION_GROUP_SCHEMA
        },
        "knowledge_bases": {
            "type": "array",
            "items": KNOWLEDGE_BASE_SCHEMA
        },
        "collaborators": {
            "type": "array",
            "items": COLLABORATOR_SCHEMA
        },
        "guardrails": GUARDRAIL_SCHEMA,
        "tags": {
            "type": "object",
            "maxProperties": 50,
            "patternProperties": {
                "^.{1,128}$": {
                    "type": "string",
                    "maxLength": 256
                }
            }
        }
    }
}


class AgentConfigSchemaValidator:
    """JSON Schema validator for agent configurations."""
    
    def __init__(self):
        """Initialize the schema validator."""
        try:
            import jsonschema
            self.jsonschema = jsonschema
            self.validator = jsonschema.Draft7Validator(AGENT_CONFIG_SCHEMA)
        except ImportError:
            raise ImportError("jsonschema package is required for schema validation. Install with: pip install jsonschema")
    
    def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, list]:
        """
        Validate agent configuration against JSON schema.
        
        Args:
            config_data: Configuration data to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Validate against schema
            schema_errors = list(self.validator.iter_errors(config_data))
            
            for error in schema_errors:
                error_path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
                errors.append(f"Schema validation error at {error_path}: {error.message}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Schema validation failed: {e}")
            return False, errors
    
    def validate_config_file(self, config_file_path: str) -> tuple[bool, list]:
        """
        Validate agent configuration file against JSON schema.
        
        Args:
            config_file_path: Path to configuration file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            with open(config_file_path, 'r') as f:
                config_data = json.load(f)
            return self.validate_config(config_data)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except FileNotFoundError:
            return False, [f"Configuration file not found: {config_file_path}"]
        except Exception as e:
            return False, [f"Error reading configuration file: {e}"]
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the complete agent configuration schema."""
        return AGENT_CONFIG_SCHEMA
    
    def save_schema(self, output_path: str) -> None:
        """
        Save the agent configuration schema to a file.
        
        Args:
            output_path: Path to save the schema file
        """
        with open(output_path, 'w') as f:
            json.dump(AGENT_CONFIG_SCHEMA, f, indent=2)


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate agent configurations against JSON schema')
    parser.add_argument('config_files', nargs='*', help='Configuration files to validate')
    parser.add_argument('--save-schema', help='Save schema to file')
    parser.add_argument('--print-schema', action='store_true', help='Print schema to stdout')
    
    args = parser.parse_args()
    
    try:
        validator = AgentConfigSchemaValidator()
    except ImportError as e:
        print(f"Error: {e}")
        return 1
    
    if args.save_schema:
        validator.save_schema(args.save_schema)
        print(f"Schema saved to: {args.save_schema}")
        return 0
    
    if args.print_schema:
        print(json.dumps(validator.get_schema(), indent=2))
        return 0
    
    if not args.config_files:
        print("No configuration files specified. Use --help for usage information.")
        return 1
    
    # Validate configuration files
    all_valid = True
    
    for config_file in args.config_files:
        is_valid, errors = validator.validate_config_file(config_file)
        
        if is_valid:
            print(f"✓ {config_file}: Valid")
        else:
            print(f"✗ {config_file}: Invalid")
            for error in errors:
                print(f"  - {error}")
            all_valid = False
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    exit(main())