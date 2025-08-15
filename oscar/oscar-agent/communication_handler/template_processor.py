#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Template processing for Communication Handler.
"""

import logging
import re
import string
from typing import Any, Dict
from config import config

logger = logging.getLogger(__name__)


class TemplateProcessor:
    """Handles message template processing and metrics collection."""
    
    @staticmethod
    def determine_message_type_from_query(query: str) -> str:
        """Determine message type from user query.
        
        Args:
            query: User's natural language query
            
        Returns:
            Message type string
        """
        query_lower = query.lower()
        
        if 'missing release notes' in query_lower or 'release notes' in query_lower:
            return 'missing_release_notes'
        elif 'criteria not met' in query_lower or 'entrance criteria' in query_lower:
            return 'criteria_not_met'
        elif 'documentation' in query_lower and ('missing' in query_lower or 'issue' in query_lower):
            return 'documentation_issues'
        elif 'code coverage' in query_lower or 'coverage' in query_lower:
            return 'missing_code_coverage'
        elif 'release announcement' in query_lower or 'announce release' in query_lower:
            return 'release_announcement'
        else:
            return 'missing_release_notes'  # Default
    
    @staticmethod
    def generate_message_with_metrics(message_type: str, query: str) -> str:
        """Generate complete message by collecting metrics and filling template.
        
        Args:
            message_type: Type of message to generate
            query: Original user query
            
        Returns:
            Complete message with real data
        """
        try:
            # Get template
            template_info = config.message_templates.get(message_type)
            if not template_info:
                return f"Automated notification: {query}"
            
            template = template_info['template']
            
            # Collect metrics based on message type
            if message_type == 'missing_release_notes':
                metrics_data = TemplateProcessor._collect_release_notes_metrics(query)
            else:
                metrics_data = {}
            
            # Fill template with metrics data
            try:
                formatted_message = template.format(**metrics_data)
                return formatted_message
            except KeyError as e:
                logger.warning(f"Missing template variable {e}, using partial formatting")
                # Leave missing variables as placeholders
                formatter = string.Formatter()
                formatted_parts = []
                for literal_text, field_name, format_spec, conversion in formatter.parse(template):
                    formatted_parts.append(literal_text)
                    if field_name is not None:
                        if field_name in metrics_data:
                            formatted_parts.append(str(metrics_data[field_name]))
                        else:
                            formatted_parts.append(f'{{{field_name}}}')
                return ''.join(formatted_parts)
                
        except Exception as e:
            logger.error(f"Error generating message with metrics: {e}")
            return f"Automated notification: {query}"
    
    @staticmethod
    def process_template_message(message_type: str, content: str, params: Dict[str, Any]) -> str:
        """Process a message using a predefined template.
        
        Args:
            message_type: Type of message template to use
            content: Base content for the message
            params: Additional parameters for template substitution
            
        Returns:
            Processed message content
        """
        try:
            template_info = config.message_templates.get(message_type)
            if not template_info:
                return content
            
            template = template_info['template']
            
            # Extract variables from content and params
            variables = {}
            
            # Extract version/branch from query
            version_match = re.search(config.patterns['version'], content.lower())
            if version_match:
                version = version_match.group(1)
                variables['branch'] = f'{version}'
                variables['version'] = version
                variables['release_version'] = version
            
            # Add any additional parameters from params
            variables.update(params)
            
            # Format template with variables, handling missing variables gracefully
            try:
                formatted_message = template.format(**variables)
                return formatted_message
            except KeyError as e:
                logger.warning(f"Missing template variable {e}, using partial formatting")
                # Try to format with available variables, leaving missing ones as placeholders
                formatter = string.Formatter()
                formatted_parts = []
                for literal_text, field_name, format_spec, conversion in formatter.parse(template):
                    formatted_parts.append(literal_text)
                    if field_name is not None:
                        if field_name in variables:
                            formatted_parts.append(str(variables[field_name]))
                        else:
                            formatted_parts.append(f'{{{field_name}}}')
                return ''.join(formatted_parts)
                
        except Exception as e:
            logger.error(f"Error processing template message: {e}")
            return content
    
    @staticmethod
    def _collect_release_notes_metrics(query: str) -> Dict[str, Any]:
        """Collect release notes metrics from the ReleaseReadinessSpecialist agent.
        
        Args:
            query: Original user query
            
        Returns:
            Dictionary with metrics data for template filling
        """
        try:
            # Extract version from query
            version_match = re.search(config.patterns['version'], query.lower())
            version = version_match.group(1) if version_match else config.default_version
            
            # Query the ReleaseReadinessSpecialist for release notes metrics
            metrics_query = f"What are the current release notes metrics for OpenSearch version {version}? Which components are missing release notes?"
            
            logger.info(f"Querying metrics for version {version}")
            
            # For now, return basic data - in production this would call the metrics agent
            # TODO: Implement actual Bedrock agent invocation
            return {
                'branch': version,
                'version': version,
                'release_version': version,
                'component_name': 'OpenSearch components',
                'components_missing': 'Multiple components'
            }
            
        except Exception as e:
            logger.error(f"Error collecting release notes metrics: {e}")
            return {'branch': config.default_version, 'version': config.default_version}