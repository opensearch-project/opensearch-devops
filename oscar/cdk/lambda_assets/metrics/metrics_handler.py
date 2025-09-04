#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Metrics Handler for Metrics Lambda Functions.

This module provides the main metrics query handling logic,
coordinating between different query types and data processors.

Functions:
    handle_metrics_query: Main metrics query handler
"""

import logging
from typing import Any, Dict, List, Optional

from data_processors import extract_test_results, extract_build_results, extract_release_results, deduplicate_integration_test_results
from query_builders import query_integration_test_results, query_distribution_build_results, query_release_readiness
from summary_generators import generate_integration_summary, generate_build_summary, generate_release_summary

logger = logging.getLogger(__name__)


def handle_metrics_query(agent_type: str, function_name: str, params: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
    """Simplified metrics query handler - execute query with parameters and return results.
    
    Args:
        agent_type: Type of agent (integration-test, build-metrics, release-metrics)
        function_name: Name of the function being called
        params: Parameters for the query
        request_id: Optional request ID for logging
        
    Returns:
        Dictionary containing query results and metadata
    """
    try:
        req_id = request_id or "unknown"
        logger.info(f"METRICS_QUERY [{req_id}]: Starting metrics query handler")
        logger.info(f"METRICS_QUERY [{req_id}]: agent_type={agent_type}, function_name={function_name}")
        logger.info(f"METRICS_QUERY [{req_id}]: params keys: {list(params.keys()) if isinstance(params, dict) else 'Not a dict'}")
        
        # Log all parameters for debugging
        for key, value in params.items():
            logger.info(f"METRICS_QUERY [{req_id}]: param {key} = {value}")
        
        # Extract parameters directly from the event
        version = params.get('version')
        rc_numbers = params.get('rc_numbers') or []
        build_numbers = params.get('build_numbers') or []
        integ_test_build_numbers = params.get('integ_test_build_numbers') or []
        components = params.get('components') or []
        status_filter = params.get('status_filter')  # 'passed', 'failed', or None
        distribution = params.get('distribution')  # Don't default to 'tar' - let all distributions through
        architecture = params.get('architecture')
        platform = params.get('platform')  # Don't default - let all platforms through
        with_security = params.get('with_security')  # 'pass', 'fail', or None
        without_security = params.get('without_security')  # 'pass', 'fail', or None
        
        # Validate required parameters
        if not version:
            return {'error': 'Version is required for metrics queries'}
        
        # Function-specific validation
        if function_name == 'get_integration_test_metrics' and not rc_numbers:
            logger.warning(f"METRICS_QUERY [{req_id}]: get_integration_test_metrics called without rc_numbers")
        elif function_name == 'get_build_metrics' and not (build_numbers or rc_numbers):
            logger.warning(f"METRICS_QUERY [{req_id}]: get_build_metrics called without build_numbers or rc_numbers")
        elif function_name == 'get_release_metrics' and not components:
            logger.warning(f"METRICS_QUERY [{req_id}]: get_release_metrics called without components")
        
        # Normalize array parameters - these should already be handled in the main parameter processing
        # but keep this as a safety net for any edge cases
        if isinstance(rc_numbers, str):
            rc_numbers = [item.strip() for item in rc_numbers.split(',') if item.strip()]
        if isinstance(build_numbers, str):
            build_numbers = [item.strip() for item in build_numbers.split(',') if item.strip()]
        if isinstance(integ_test_build_numbers, str):
            integ_test_build_numbers = [item.strip() for item in integ_test_build_numbers.split(',') if item.strip()]
        if isinstance(components, str):
            components = [item.strip() for item in components.split(',') if item.strip()]
        
        # Ensure arrays are not None
        rc_numbers = rc_numbers or []
        build_numbers = build_numbers or []
        integ_test_build_numbers = integ_test_build_numbers or []
        components = components or []
        
        logger.info(f"METRICS_QUERY [{req_id}]: Executing {agent_type} query for version {version}")
        logger.info(f"METRICS_QUERY [{req_id}]: Parameters - rc_numbers={rc_numbers}, build_numbers={build_numbers}, components={components}")
        logger.info(f"METRICS_QUERY [{req_id}]: About to execute query based on agent type")
        
        # Execute single query based on agent type
        if agent_type in ['integration-test', 'test-metrics', 'test']:
            logger.info(f"METRICS_QUERY [{req_id}]: Processing integration test query")
            rc_number_to_use = rc_numbers[0] if rc_numbers else None
            logger.info(f"METRICS_QUERY [{req_id}]: Using RC number: {rc_number_to_use} (from rc_numbers: {rc_numbers})")
            
            logger.info(f"METRICS_QUERY [{req_id}]: About to call query_integration_test_results")
            logger.info(f"METRICS_QUERY [{req_id}]: Query parameters - version={version}, rc_number={rc_number_to_use}, build_numbers={build_numbers}, components={components}")
            logger.info(f"METRICS_QUERY [{req_id}]: Filters - status_filter={status_filter}, distribution={distribution}, architecture={architecture}, platform={platform}")
            logger.info(f"METRICS_QUERY [{req_id}]: Security filters - with_security={with_security}, without_security={without_security}")
            
            opensearch_results = query_integration_test_results(
                version=version,
                rc_number=rc_number_to_use,
                build_numbers=build_numbers if build_numbers else None,
                components=components if components else None,
                status_filter=status_filter,
                distribution=distribution,
                architecture=architecture,
                platform=platform,
                with_security=with_security,
                without_security=without_security,
                integ_test_build_numbers=integ_test_build_numbers if integ_test_build_numbers else None
            )
            logger.info(f"METRICS_QUERY [{req_id}]: query_integration_test_results completed")
            data_source = 'opensearch-integration-test-results'
            
        elif agent_type in ['build-metrics', 'build']:
            opensearch_results = query_distribution_build_results(
                version=version,
                build_numbers=build_numbers if build_numbers else None,
                components=components if components else None,
                status_filter=status_filter
            )
            data_source = 'opensearch-distribution-build-results'
            
        elif agent_type in ['release-metrics', 'release']:
            opensearch_results = query_release_readiness(
                version=version,
                components=components if components else None
            )
            data_source = 'opensearch_release_metrics'
            
        else:
            return {'error': f'Unknown agent type: {agent_type}'}
        
        # Extract and process results based on agent type
        logger.info(f"METRICS_QUERY [{req_id}]: About to extract results for agent type: {agent_type}")
        logger.info(f"METRICS_QUERY [{req_id}]: Function name: {function_name}")
        logger.info(f"METRICS_QUERY [{req_id}]: Data source will be: {data_source}")
        
        if agent_type in ['integration-test', 'test-metrics', 'test']:
            logger.info(f"METRICS_QUERY [{req_id}]: Calling extract_test_results for integration test data")
            results = extract_test_results(opensearch_results)
            logger.info(f"METRICS_QUERY [{req_id}]: extract_test_results completed, got {len(results)} results")
        elif agent_type in ['build-metrics', 'build']:
            results = extract_build_results(opensearch_results)
        elif agent_type in ['release-metrics', 'release']:
            results = extract_release_results(opensearch_results)
        else:
            # Fallback to raw extraction - but check if this is integration test data
            hits = opensearch_results.get('hits', {}).get('hits', [])
            raw_results = [hit.get('_source', {}) for hit in hits]
            
            # If this looks like integration test data, apply deduplication
            if raw_results and any('with_security' in r and 'without_security' in r for r in raw_results):
                logger.info(f"METRICS_QUERY [{req_id}]: Fallback case detected integration test data, applying deduplication")
                results = deduplicate_integration_test_results(raw_results)
            else:
                logger.info(f"METRICS_QUERY [{req_id}]: Fallback case - raw results don't look like integration test data")
                results = raw_results
        
        # Apply filtering AFTER deduplication to ensure we get the most recent results first
        # This is critical - if we filter before deduplication, we might miss more recent results
        # that have different statuses than what we're filtering for
        if status_filter:
            if agent_type in ['integration-test', 'test-metrics', 'test']:
                results = [r for r in results if r.get('component_build_result') == status_filter]
            elif agent_type in ['build-metrics', 'build']:
                results = [r for r in results if r.get('component_build_result') == status_filter]
        
        if with_security:
            results = [r for r in results if r.get('with_security') == with_security]
        if without_security:
            results = [r for r in results if r.get('without_security') == without_security]
        
        logger.info(f"METRICS_QUERY [{req_id}]: Query returned {len(results)} results after filtering")
        logger.info(f"METRICS_QUERY [{req_id}]: About to create final response")

        # Generate appropriate summary based on agent type
        if agent_type in ['integration-test', 'test-metrics', 'test']:
            summary = generate_integration_summary(results)
        elif agent_type in ['build-metrics', 'build']:
            summary = generate_build_summary(results)
        elif agent_type in ['release-metrics', 'release']:
            summary = generate_release_summary(results)
        else:
            # Fallback on emptysummary
            summary = {}
        
        # Return results directly - let the LLM interpret them
        return {
            'agent_type': agent_type,
            'version': version,
            'query_parameters': {
                'rc_numbers': rc_numbers,
                'build_numbers': build_numbers,
                'integ_test_build_numbers': integ_test_build_numbers,
                'components': components,
                'status_filter': status_filter,
                'distribution': distribution,
                'architecture': architecture,
                'platform': platform,
                'with_security': with_security,
                'without_security': without_security
            },
            'data_source': data_source,
            'total_results': len(results),
            'results': results,
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Metrics query failed: {e}")
        return {'error': str(e), 'type': 'metrics_error'}