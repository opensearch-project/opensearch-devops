#!/usr/bin/env python3
"""
Jenkins Lambda Function

AWS Lambda handler for Jenkins operations. This function provides the interface
between Bedrock agents and the Jenkins client, handling job triggers and status checks.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Jenkins client components
from jenkins_client import JenkinsClient
from job_definitions import job_registry
from config import config



def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for Jenkins operations.
    
    Args:
        event: Lambda event containing function name and parameters
        context: Lambda context object
        
    Returns:
        Response dictionary with results
    """
    try:
        logger.info("🚀 JENKINS LAMBDA: Handler started")
        logger.info(f"🚀 JENKINS LAMBDA: Full event received: {json.dumps(event, indent=2)}")
        
        # Extract function and parameters from event
        function_name = event.get('function', '')
        parameters = event.get('parameters', [])
        
        logger.info(f"🚀 JENKINS LAMBDA: Extracted function_name='{function_name}'")
        logger.info(f"🚀 JENKINS LAMBDA: Raw parameters: {parameters}")
        
        # Convert parameters list to dictionary
        params = {}
        for param in parameters:
            if isinstance(param, dict) and 'name' in param and 'value' in param:
                params[param['name']] = param['value']
        
        logger.info(f"🚀 JENKINS LAMBDA: Converted parameters: {params}")
        
        logger.info(f"🚀 JENKINS LAMBDA: Authorization handled by supervisor agent")
        logger.info(f"🚀 JENKINS LAMBDA: About to initialize JenkinsClient")
        
        # Initialize Jenkins client
        jenkins_client = JenkinsClient()
        logger.info(f"🚀 JENKINS LAMBDA: JenkinsClient initialized successfully")
        
        # Route to appropriate handler
        print(f"🔀 JENKINS LAMBDA: Routing to function '{function_name}'")
        logger.info(f"🔀 JENKINS LAMBDA: Routing to function '{function_name}'")
        
        if function_name == 'trigger_job':
            print("🔀 JENKINS LAMBDA: *** CALLING TRIGGER_JOB - THIS WILL EXECUTE THE JOB ***")
            logger.info("🔀 JENKINS LAMBDA: Routing to handle_trigger_job")
            result = handle_trigger_job(jenkins_client, params)
        elif function_name == 'test_connection':
            print("🔀 JENKINS LAMBDA: Routing to handle_test_connection")
            logger.info("🔀 JENKINS LAMBDA: Routing to handle_test_connection")
            result = handle_test_connection(jenkins_client)
        elif function_name == 'get_job_info':
            print("🔀 JENKINS LAMBDA: *** CALLING GET_JOB_INFO - INFORMATION ONLY ***")
            logger.info("🔀 JENKINS LAMBDA: Routing to handle_get_job_info")
            result = handle_get_job_info(jenkins_client, params)
        elif function_name == 'list_jobs':
            logger.info("🔀 JENKINS LAMBDA: Routing to handle_list_jobs")
            result = handle_list_jobs(jenkins_client)
        else:
            logger.error(f"❌ JENKINS LAMBDA: Unknown function '{function_name}'")
            result = {
                'status': 'error',
                'message': f'Unknown function: {function_name}',
                'available_functions': [
                    'trigger_job', 'test_connection', 
                    'get_job_info', 'list_jobs'
                ]
            }
        
        logger.info(f"✅ JENKINS LAMBDA: Function '{function_name}' completed with status: {result.get('status', 'unknown')}")
        
        return create_response(event, result)
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}", exc_info=True)
        return create_response(event, {
            'status': 'error',
            'message': 'Internal Lambda error',
            'error': str(e),
            'type': 'lambda_error'
        })

def format_parameters_as_bullets(parameter_definitions: Dict[str, Dict[str, Any]]) -> str:
    """
    Format job parameters as a bullet list for better readability.
    
    Args:
        parameter_definitions: Dictionary of parameter definitions
        
    Returns:
        Formatted string with bullet points
    """
    if not parameter_definitions:
        return "• No parameters required"
    
    lines = []
    for param_name, param_info in parameter_definitions.items():
        description = param_info.get('description', 'No description')
        required = param_info.get('required', False)
        param_type = param_info.get('type', 'string')
        default = param_info.get('default')
        choices = param_info.get('choices')
        
        # Build a clean parameter line - just name and description for required params
        if required:
            line = f"• {param_name} - {description}"
        else:
            line = f"• {param_name} (Optional) - {description}"
            
            # Add default value for optional parameters
            if default is not None:
                line += f" (Default: {default})"
        
        # Add choices if present
        if choices:
            line += f" (Options: {', '.join(choices)})"
        
        lines.append(line)
    
    return "\n".join(lines)

def handle_trigger_job(jenkins_client: JenkinsClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle generic job triggering with mandatory confirmation check.
    
    Args:
        jenkins_client: Jenkins client instance
        params: Parameters including job_name, confirmed, and individual job parameters
        
    Returns:
        Job trigger result
    """
    job_name = params.get('job_name')
    confirmed = params.get('confirmed')
    authorized = params.get('authorized')
    
    logger.info(f"🚀 JENKINS LAMBDA: handle_trigger_job called with job_name='{job_name}', confirmed={confirmed}, authorized={authorized}")
    logger.info(f"🚀 JENKINS LAMBDA: This function WILL make HTTP requests to Jenkins")
    
    # CRITICAL: Check confirmation parameter first
    if confirmed is None:
        logger.error("❌ JENKINS LAMBDA: Missing required 'confirmed' parameter")
        return {
            'status': 'error',
            'message': 'SECURITY ERROR: The "confirmed" parameter is required for job execution. Use get_job_info first to get job details, then call trigger_job with confirmed=true after user confirmation.',
            'job_name': job_name,
            'required_parameters': ['job_name', 'confirmed', 'authorized']
        }
    
    # Convert string values to boolean (Bedrock passes booleans as strings)
    if isinstance(confirmed, str):
        if confirmed.strip().lower() in ['true', '1', 'yes']:
            confirmed = True
            logger.info(f"✅ JENKINS LAMBDA: Converted string '{params.get('confirmed')}' to boolean True")
        elif confirmed.strip().lower() in ['false', '0', 'no']:
            confirmed = False
            logger.info(f"🚫 JENKINS LAMBDA: Converted string '{params.get('confirmed')}' to boolean False")
        else:
            logger.error(f"❌ JENKINS LAMBDA: Invalid 'confirmed' parameter value: '{confirmed}'")
            return {
                'status': 'error',
                'message': f'SECURITY ERROR: The "confirmed" parameter must be "true" or "false", got: "{confirmed}"',
                'job_name': job_name,
                'confirmed_value': confirmed
            }
    elif not isinstance(confirmed, bool):
        logger.error(f"❌ JENKINS LAMBDA: Invalid 'confirmed' parameter type: {type(confirmed)}")
        return {
            'status': 'error',
            'message': f'SECURITY ERROR: The "confirmed" parameter must be a boolean or string, got: {type(confirmed).__name__}',
            'job_name': job_name,
            'confirmed_value': confirmed
        }
    
    if confirmed is False:
        logger.warning(f"🚫 JENKINS LAMBDA: Job execution blocked - confirmed=false for job '{job_name}'")
        return {
            'status': 'error',
            'message': 'Job execution cancelled. The "confirmed" parameter is false. Set confirmed=true only after user explicitly confirms job execution.',
            'job_name': job_name,
            'confirmed': False
        }
    
    logger.info(f"✅ JENKINS LAMBDA: Confirmation check passed - proceeding with authorization check")
    
    # CRITICAL: Check authorization parameter
    if authorized is None:
        logger.error("❌ JENKINS LAMBDA: Missing required 'authorized' parameter")
        return {
            'status': 'error',
            'message': 'SECURITY ERROR: The "authorized" parameter is required for job execution. User must be verified as authorized before job execution.',
            'job_name': job_name,
            'required_parameters': ['job_name', 'confirmed', 'authorized']
        }
    
    # Convert string values to boolean (Bedrock passes booleans as strings)
    if isinstance(authorized, str):
        if authorized.strip().lower() in ['true', '1', 'yes']:
            authorized = True
            logger.info(f"✅ JENKINS LAMBDA: Converted string '{params.get('authorized')}' to boolean True")
        elif authorized.strip().lower() in ['false', '0', 'no']:
            authorized = False
            logger.info(f"🚫 JENKINS LAMBDA: Converted string '{params.get('authorized')}' to boolean False")
        else:
            logger.error(f"❌ JENKINS LAMBDA: Invalid 'authorized' parameter value: '{authorized}'")
            return {
                'status': 'error',
                'message': f'SECURITY ERROR: The "authorized" parameter must be "true" or "false", got: "{authorized}"',
                'job_name': job_name,
                'authorized_value': authorized
            }
    elif not isinstance(authorized, bool):
        logger.error(f"❌ JENKINS LAMBDA: Invalid 'authorized' parameter type: {type(authorized)}")
        return {
            'status': 'error',
            'message': f'SECURITY ERROR: The "authorized" parameter must be a boolean or string, got: {type(authorized).__name__}',
            'job_name': job_name,
            'authorized_value': authorized
        }
    
    if authorized is False:
        logger.warning(f"🚫 JENKINS LAMBDA: Job execution blocked - user not authorized for job '{job_name}'")
        return {
            'status': 'error',
            'message': 'Access denied. You are not authorized to execute Jenkins jobs. Please contact your system administrator.',
            'job_name': job_name,
            'authorized': False,
            'error_type': 'authorization_error'
        }
    
    logger.info(f"✅ JENKINS LAMBDA: Authorization check passed - proceeding with job execution")
    
    if not job_name:
        logger.error("❌ JENKINS LAMBDA: Missing job_name parameter")
        return {
            'status': 'error',
            'message': 'job_name parameter is required for trigger_job function',
            'available_jobs': job_registry.list_jobs()
        }
    
    # Extract job parameters (all params except job_name, confirmed, and authorized)
    job_params = {k: v for k, v in params.items() if k not in ['job_name', 'confirmed', 'authorized']}
    logger.info(f"🚀 JENKINS LAMBDA: Extracted job parameters: {job_params}")
    
    # Handle legacy job_parameters JSON string if provided
    job_parameters_json = params.get('job_parameters')
    if job_parameters_json:
        logger.info(f"🚀 JENKINS LAMBDA: Found legacy job_parameters JSON: {job_parameters_json}")
        try:
            import json
            parsed_params = json.loads(job_parameters_json)
            job_params.update(parsed_params)
            logger.info(f"🚀 JENKINS LAMBDA: Updated job_params with JSON: {job_params}")
        except json.JSONDecodeError:
            logger.error("❌ JENKINS LAMBDA: Invalid JSON in job_parameters field")
            return {
                'status': 'error',
                'message': 'Invalid JSON in job_parameters field',
                'job_name': job_name
            }
    
    logger.info(f"🚀 JENKINS LAMBDA: About to call jenkins_client.trigger_job with job_name='{job_name}', params={job_params}")
    result = jenkins_client.trigger_job(job_name, job_params)
    logger.info(f"🚀 JENKINS LAMBDA: trigger_job returned status: {result.get('status', 'unknown')}")
    
    # Enhance the success message to include only workflow URL if available
    if result.get('status') == 'success':
        job_url = result.get('job_url', '')
        queue_location = result.get('queue_location', '')
        workflow_url = result.get('workflow_url')
        
        # Remove queue_location from the result to prevent agent from displaying it
        if 'queue_location' in result:
            del result['queue_location']
        
        if workflow_url:
            # Only show workflow URL in the response message and remove from result to avoid duplication
            result['message'] = (
                f"Success! I've triggered the {job_name} job for {job_params}.\n"
                f"You can monitor the job progress at: {workflow_url}"
            )
            # Remove workflow_url from result to prevent agent from displaying it separately
            if 'workflow_url' in result:
                del result['workflow_url']
        else:
            # Fallback message when workflow URL is not yet available
            result['message'] = (
                f"Success! I've triggered the {job_name} job for {job_params}.\n"
                f"The job has been queued and will start executing shortly.\n"
                f"Note: Workflow URL will be available once the job starts executing."
            )
    
    return result

def handle_test_connection(jenkins_client: JenkinsClient) -> Dict[str, Any]:
    """
    Handle Jenkins connection test.
    
    Args:
        jenkins_client: Jenkins client instance
        
    Returns:
        Connection test result
    """
    return jenkins_client.test_connection()

def handle_get_job_info(jenkins_client: JenkinsClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle getting job information.
    
    Args:
        jenkins_client: Jenkins client instance
        params: Parameters including job_name
        
    Returns:
        Job information result
    """
    job_name = params.get('job_name', 'docker-scan')  # Default to docker-scan
    logger.info(f"📋 JENKINS LAMBDA: handle_get_job_info called with job_name='{job_name}'")
    logger.info(f"📋 JENKINS LAMBDA: This function should NOT make HTTP requests to Jenkins")
    
    result = jenkins_client.get_job_info(job_name)
    logger.info(f"📋 JENKINS LAMBDA: get_job_info returned status: {result.get('status', 'unknown')}")
    
    # Format parameters as bullet list for better readability
    if result.get('status') == 'success' and 'parameter_definitions' in result:
        formatted_params = format_parameters_as_bullets(result['parameter_definitions'])
        
        # Create a clean, structured message
        description = result.get('description', 'No description available')
        job_url = result.get('job_url', '')
        
        message_parts = [
            f"I've found the {job_name} job information. Here are the details:",
            f"",
            f"Job: {job_name}",
            f"Description: {description}",
            f"",
            f"Required parameters:",
            formatted_params
        ]
        
        if job_url:
            message_parts.extend(["", f"Job URL: {job_url}"])
        
        result['message'] = "\n".join(message_parts)
        
        # Keep the formatted parameters for potential future use
        result['formatted_parameters'] = formatted_params
    
    return result

def handle_list_jobs(jenkins_client: JenkinsClient) -> Dict[str, Any]:
    """
    Handle listing available jobs.
    
    Args:
        jenkins_client: Jenkins client instance
        
    Returns:
        Available jobs list
    """
    result = jenkins_client.list_available_jobs()
    
    # Format the jobs list with bullet points for better readability
    if result.get('status') == 'success' and 'jobs' in result:
        jobs_info = result['jobs']
        formatted_jobs = []
        
        for job_name, job_info in jobs_info.items():
            description = job_info.get('description', 'No description')
            param_count = len(job_info.get('parameters', {}))
            formatted_jobs.append(f"• {job_name}: {description} ({param_count} parameters)")
        
        result['message'] = f"Available Jenkins jobs:\n\n" + "\n".join(formatted_jobs)
    
    return result

def create_response(event: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a standardized Lambda response for Bedrock action groups.
    
    Args:
        event: Original Lambda event
        result: Result dictionary to return
        
    Returns:
        Properly formatted Bedrock action group response
    """
    action_group = event.get('actionGroup', 'jenkins-operations')
    function = event.get('function', 'unknown')
    
    logger.info(f"Creating Bedrock response for action_group={action_group}, function={function}")
    
    # Serialize result to JSON string as required by Bedrock
    response_body_string = json.dumps(result, default=str)
    
    # Create the proper Bedrock action group response format
    bedrock_response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": response_body_string
                    }
                }
            }
        }
    }
    
    logger.info(f"Created Bedrock response with body length: {len(response_body_string)}")
    return bedrock_response

# For local testing
if __name__ == "__main__":
    # Test event for central release promotion
    test_event = {
        "function": "trigger_job",
        "parameters": [
            {"name": "job_name", "value": "Pipeline central-release-promotion"},
            {"name": "RELEASE_VERSION", "value": "2.11.0"},
            {"name": "OPENSEARCH_RC_BUILD_NUMBER", "value": "123"},
            {"name": "OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER", "value": "456"}
        ]
    }
    
    class MockContext:
        pass
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))