"""
Configuration loader utility for reading JSON configs and environment variables.
Supports loading from .env files, environment variables, and AWS Secrets Manager.
"""

import json
import os
from typing import Dict, Any, Optional, Union
from pathlib import Path
import boto3
from botocore.exceptions import ClientError


class ConfigLoader:
    """Utility class for loading configuration from various sources."""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the configuration loader.
        
        Args:
            region: AWS region for Secrets Manager access
        """
        self.region = region
        self._secrets_client = None
    
    @property
    def secrets_client(self):
        """Lazy initialization of Secrets Manager client."""
        if self._secrets_client is None:
            self._secrets_client = boto3.client('secretsmanager', region_name=self.region)
        return self._secrets_client
    
    def load_env_file(self, env_file_path: str = ".env") -> Dict[str, str]:
        """
        Load environment variables from a .env file.
        
        Args:
            env_file_path: Path to the .env file
            
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        env_path = Path(env_file_path)
        
        if not env_path.exists():
            raise FileNotFoundError(f"Environment file not found: {env_file_path}")
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        return env_vars
    
    def load_from_secrets_manager(self, secret_name: str) -> Dict[str, str]:
        """
        Load configuration from AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret in Secrets Manager
            
        Returns:
            Dictionary of configuration values
        """
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            secret_string = response['SecretString']
            return json.loads(secret_string)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                raise ValueError(f"Secret not found: {secret_name}")
            elif error_code == 'InvalidRequestException':
                raise ValueError(f"Invalid request for secret: {secret_name}")
            elif error_code == 'InvalidParameterException':
                raise ValueError(f"Invalid parameter for secret: {secret_name}")
            else:
                raise e
    
    def load_json_config(self, config_file_path: str) -> Dict[str, Any]:
        """
        Load configuration from a JSON file.
        
        Args:
            config_file_path: Path to the JSON configuration file
            
        Returns:
            Dictionary of configuration values
        """
        config_path = Path(config_file_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def get_config_value(self, key: str, default: Optional[str] = None, 
                        secret_name: Optional[str] = None) -> Optional[str]:
        """
        Get a configuration value from multiple sources with fallback priority:
        1. AWS Secrets Manager (if secret_name provided)
        2. Environment variables
        3. Default value
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key not found
            secret_name: Optional secret name to check first
            
        Returns:
            Configuration value or default
        """
        # Try Secrets Manager first if specified
        if secret_name:
            try:
                secrets = self.load_from_secrets_manager(secret_name)
                if key in secrets:
                    return secrets[key]
            except (ValueError, ClientError):
                # Fall back to environment variables if secrets access fails
                pass
        
        # Try environment variables
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        
        # Return default value
        return default
    
    def load_merged_config(self, env_file_path: str = ".env", 
                          secret_name: Optional[str] = None) -> Dict[str, str]:
        """
        Load and merge configuration from multiple sources.
        Priority: Secrets Manager > Environment Variables > .env file
        
        Args:
            env_file_path: Path to the .env file
            secret_name: Optional secret name for Secrets Manager
            
        Returns:
            Merged configuration dictionary
        """
        config = {}
        
        # Start with .env file
        try:
            config.update(self.load_env_file(env_file_path))
        except FileNotFoundError:
            pass  # .env file is optional
        
        # Override with environment variables
        for key, value in os.environ.items():
            config[key] = value
        
        # Override with Secrets Manager if specified
        if secret_name:
            try:
                secrets = self.load_from_secrets_manager(secret_name)
                config.update(secrets)
            except (ValueError, ClientError):
                pass  # Secrets Manager is optional fallback
        
        return config
    
    def validate_required_config(self, config: Dict[str, str], 
                                required_keys: list) -> bool:
        """
        Validate that all required configuration keys are present.
        
        Args:
            config: Configuration dictionary to validate
            required_keys: List of required configuration keys
            
        Returns:
            True if all required keys are present
            
        Raises:
            ValueError: If any required keys are missing
        """
        missing_keys = [key for key in required_keys if key not in config or not config[key]]
        
        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")
        
        return True