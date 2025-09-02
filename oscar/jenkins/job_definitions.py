#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.


#!/usr/bin/env python3
"""
Jenkins Job Definitions

This module defines the structure and parameters for different Jenkins jobs,
providing a modular system for adding new jobs with proper validation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class JobParameter:
    """Represents a Jenkins job parameter with validation."""
    name: str
    description: str
    required: bool = True
    default_value: Optional[str] = None
    parameter_type: str = "string"  # string, boolean, choice, etc.
    choices: Optional[List[str]] = None
    validation_pattern: Optional[str] = None

class BaseJobDefinition(ABC):
    """Base class for Jenkins job definitions."""
    
    def __init__(self):
        self.job_name = self.get_job_name()
        self.parameters = self.get_parameters()
        self.description = self.get_description()
    
    @abstractmethod
    def get_job_name(self) -> str:
        """Return the Jenkins job name."""
        pass
    
    @abstractmethod
    def get_parameters(self) -> List[JobParameter]:
        """Return the list of job parameters."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return a description of what this job does."""
        pass
    
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize parameters for this job.
        
        Args:
            params: Dictionary of parameter name -> value
            
        Returns:
            Dictionary of validated parameters
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        validated = {}
        
        for param_def in self.parameters:
            param_name = param_def.name
            param_value = params.get(param_name)
            
            # Check required parameters
            if param_def.required and param_value is None:
                if param_def.default_value is not None:
                    param_value = param_def.default_value
                else:
                    raise ValueError(f"Required parameter '{param_name}' is missing")
            
            # Skip None values for optional parameters
            if param_value is None:
                continue
            
            # Validate choices
            if param_def.choices and param_value not in param_def.choices:
                raise ValueError(
                    f"Parameter '{param_name}' must be one of {param_def.choices}, got '{param_value}'"
                )
            
            # Type conversion and validation
            if param_def.parameter_type == "boolean":
                if isinstance(param_value, str):
                    param_value = param_value.lower() in ('true', '1', 'yes', 'on')
                param_value = bool(param_value)
            elif param_def.parameter_type == "string":
                param_value = str(param_value)
            
            # Validate pattern if specified
            if param_def.validation_pattern and param_def.parameter_type == "string":
                import re
                if not re.match(param_def.validation_pattern, param_value):
                    raise ValueError(
                        f"Parameter '{param_name}' does not match required pattern. "
                        f"Expected format for {param_def.description.lower()}"
                    )
            
            validated[param_name] = param_value
        
        return validated
    
    def get_parameter_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all parameters for this job."""
        param_info = {}
        for param in self.parameters:
            info = {
                'description': param.description,
                'required': param.required,
                'type': param.parameter_type,
                'default': param.default_value,
                'choices': param.choices
            }
            if param.validation_pattern:
                info['validation_pattern'] = param.validation_pattern
            param_info[param.name] = info
        return param_info

class DockerScanJob(BaseJobDefinition):
    """Docker security scan job definition."""
    
    def get_job_name(self) -> str:
        return "docker-scan"
    
    def get_description(self) -> str:
        return "Triggers a Docker security scan for the specified image"
    
    def get_parameters(self) -> List[JobParameter]:
        return [
            JobParameter(
                name="IMAGE_FULL_NAME",
                description="Full Docker image name including tag (e.g., alpine:3.19)",
                required=True,
                parameter_type="string"
            )
        ]

class CentralReleasePromotionJob(BaseJobDefinition):
    """Central release promotion pipeline job definition."""
    
    def get_job_name(self) -> str:
        return "central-release-promotion"
    
    def get_description(self) -> str:
        return "Promotes OpenSearch and OpenSearch Dashboards release candidates to final release. Requires release version and RC build numbers for both OpenSearch and OpenSearch Dashboards."
    
    def get_parameters(self) -> List[JobParameter]:
        return [
            JobParameter(
                name="RELEASE_VERSION",
                description="Release version (e.g., 2.11.0, 3.0.0)",
                required=True,
                parameter_type="string",
                validation_pattern=r"^\d+\.\d+\.\d+$"
            ),
            JobParameter(
                name="OPENSEARCH_RC_BUILD_NUMBER",
                description="OpenSearch Release Candidate Build Number",
                required=True,
                parameter_type="string"
            ),
            JobParameter(
                name="OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER",
                description="OpenSearch Dashboards Release Candidate Build Number",
                required=True,
                parameter_type="string"
            ),
            JobParameter(
                name="TAG_DOCKER_LATEST",
                description="Tag the images as latest",
                required=False,
                default_value='True',
                parameter_type='boolean'
            )
        ]

class JobRegistry:
    """Registry for managing available Jenkins jobs."""
    
    def __init__(self):
        self._jobs: Dict[str, BaseJobDefinition] = {}
        self._register_default_jobs()
    
    def _register_default_jobs(self):
        """Register the default set of Jenkins jobs."""
        self.register_job(DockerScanJob())
        self.register_job(CentralReleasePromotionJob())
    
    def register_job(self, job_definition: BaseJobDefinition):
        """Register a new job definition."""
        self._jobs[job_definition.job_name] = job_definition
        logger.info(f"Registered Jenkins job: {job_definition.job_name}")
    
    def get_job(self, job_name: str) -> Optional[BaseJobDefinition]:
        """Get a job definition by name."""
        return self._jobs.get(job_name)
    
    def list_jobs(self) -> List[str]:
        """List all registered job names."""
        return list(self._jobs.keys())
    
    def get_job_info(self, job_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a job."""
        job = self.get_job(job_name)
        if not job:
            return None
        
        return {
            'name': job.job_name,
            'description': job.description,
            'parameters': job.get_parameter_info()
        }
    
    def validate_job_parameters(self, job_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters for a specific job."""
        job = self.get_job(job_name)
        if not job:
            raise ValueError(f"Unknown job: {job_name}")
        
        return job.validate_parameters(params)

# Global job registry
job_registry = JobRegistry()