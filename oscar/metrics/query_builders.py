#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Query Builders for Metrics Lambda Functions.

This module provides query building utilities for different types of
OpenSearch queries used in the metrics system.

Functions:
    query_integration_test_results: Build and execute integration test queries
    query_distribution_build_results: Build and execute build results queries
    query_release_readiness: Build and execute release readiness queries
"""

import logging
from typing import Any, Dict, List, Optional

from aws_utils import opensearch_request
from config import config

logger = logging.getLogger(__name__)


def query_integration_test_results(
    version: str,
    rc_number: Optional[int] = None,
    build_numbers: Optional[List[str]] = None,
    components: Optional[List[str]] = None,
    status_filter: Optional[str] = None,
    distribution: Optional[str] = None,
    architecture: Optional[str] = None,
    platform: Optional[str] = None,
    with_security: Optional[str] = None,
    without_security: Optional[str] = None,
    integ_test_build_numbers: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Comprehensive integration test results query with detailed logging.
    
    Args:
        version: Version to query for
        rc_number: RC number filter
        build_numbers: Build numbers to filter by
        components: Components to filter by
        status_filter: Status filter ('passed', 'failed', or None)
        distribution: Distribution filter
        architecture: Architecture filter
        platform: Platform filter
        with_security: With security filter
        without_security: Without security filter
        integ_test_build_numbers: Integration test build numbers
        
    Returns:
        Dictionary containing OpenSearch query results
    """
    logger.info(f"INTEGRATION_QUERY: Starting integration test query")
    logger.info(f"INTEGRATION_QUERY: version={version}, rc_number={rc_number}, components={components}")
    
    # Use large size limit - we'll deduplicate results for cleaner output
    size_limit = config.large_query_size
    logger.info(f"INTEGRATION_QUERY: Using size limit: {size_limit}")

    # Build query with version and RC filters
    must_clauses = [{"match_phrase": {"version": version}}]
    
    if rc_number:
        rc_number_int = int(rc_number) if isinstance(rc_number, str) else rc_number
        must_clauses.append({"term": {"rc_number": rc_number_int}})
    
    query_body = {
        "size": size_limit,
        "sort": [{"build_start_time": {"order": "desc"}}],
        "_source": [
            "component", "component_repo", "component_repo_url", "component_build_result", 
            "distribution_build_number", "distribution_build_url", "integ_test_build_number", 
            "integ_test_build_url", "rc_number", "rc", "version", "qualifier",
            "platform", "architecture", "distribution", "component_category",
            "test_report_manifest_yml", "build_start_time",
            "with_security", "with_security_build_yml", "with_security_test_stdout", "with_security_test_stderr",
            "without_security", "without_security_build_yml", "without_security_test_stdout", "without_security_test_stderr"
        ],
        "query": {
            "bool": {
                "must": must_clauses
            }
        }
    }
    
    # Note: status_filter is NOT applied at OpenSearch level to ensure proper deduplication
    # It will be applied after deduplication in the main handler
    
    # Add build numbers filter
    if build_numbers:
        build_numbers_str = [str(bn) for bn in build_numbers]
        build_filter_clause = {"terms": {"distribution_build_number": build_numbers_str}}
        query_body["query"]["bool"]["must"].append(build_filter_clause)
    
    # Add component filter with improved Dashboards handling
    if components:
        should_clauses = []
        regular_components = []
        
        for component in components:
            if component == "OpenSearch-Dashboards":
                # Match ci-group patterns and any dashboards-related components
                dashboards_clauses = [
                    {"regexp": {"component": "OpenSearch-Dashboards-ci-group-.*"}},
                    {"regexp": {"component": ".*[Dd]ashboards.*"}}
                ]
                should_clauses.extend(dashboards_clauses)
            elif "dashboards" in component.lower():
                # Handle any dashboards-related components generically
                dashboards_clause = {"match_phrase": {"component": component}}
                should_clauses.append(dashboards_clause)
            else:
                regular_components.append(component)
        
        # Add regular components
        if regular_components:
            regular_clause = {"terms": {"component": regular_components}}
            should_clauses.append(regular_clause)
        
        if should_clauses:
            if len(should_clauses) == 1:
                query_body["query"]["bool"]["must"].append(should_clauses[0])
            else:
                component_bool_clause = {"bool": {"should": should_clauses}}
                query_body["query"]["bool"]["must"].append(component_bool_clause)
    
    # Add platform/architecture/distribution filters (only if explicitly specified)
    if distribution:
        dist_clause = {"match_phrase": {"distribution": distribution}}
        query_body["query"]["bool"]["must"].append(dist_clause)
    if architecture:
        arch_clause = {"match_phrase": {"architecture": architecture}}
        query_body["query"]["bool"]["must"].append(arch_clause)
    if platform:
        platform_clause = {"match_phrase": {"platform": platform}}
        query_body["query"]["bool"]["must"].append(platform_clause)
    
    # NOTE: status_filter, with_security, and without_security are NOT applied at OpenSearch level
    # to ensure proper deduplication. They will be applied after deduplication in the main handler
    
    # Add integration test build number filter
    if integ_test_build_numbers:
        integ_build_nums = [int(bn) for bn in integ_test_build_numbers]
        integ_clause = {"terms": {"integ_test_build_number": integ_build_nums}}
        query_body["query"]["bool"]["must"].append(integ_clause)
    
    # Execute the main query
    logger.info(f"INTEGRATION_QUERY: About to execute OpenSearch request")
    result = opensearch_request('POST', f'/{config.get_integration_test_index_pattern()}/_search', query_body)
    logger.info(f"INTEGRATION_QUERY: OpenSearch request completed")
    
    if result and 'hits' in result:
        total_hits = result['hits'].get('total', {})
        if isinstance(total_hits, dict):
            hit_count = total_hits.get('value', 0)
        else:
            hit_count = total_hits
        actual_results = len(result['hits'].get('hits', []))
        logger.info(f"INTEGRATION_QUERY: Query completed - Total matches: {hit_count}, Returned: {actual_results}")
        
        # Add metadata about result limits
        if 'metadata' not in result:
            result['metadata'] = {}
        result['metadata']['total_available'] = hit_count
        result['metadata']['returned_count'] = actual_results
        
        if hit_count > actual_results:
            result['metadata']['note'] = f"Showing first {actual_results} of {hit_count} total results. For complete data, use the OpenSearch dashboard or add filters to narrow results."
        else:
            result['metadata']['note'] = f"Query completed successfully. Showing {actual_results} results."
    else:
        logger.error("INTEGRATION_QUERY: Query failed or returned no hits structure")
    
    logger.info(f"INTEGRATION_QUERY: Returning result")
    return result


def query_distribution_build_results(
    version: str,
    build_numbers: Optional[List[str]] = None,
    components: Optional[List[str]] = None,
    status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Query distribution build results.
    
    Args:
        version: Version to query for
        build_numbers: Build numbers to filter by
        components: Components to filter by
        status_filter: Status filter ('passed', 'failed', or None)
        
    Returns:
        Dictionary containing OpenSearch query results
    """
    query_body = {
        "size": config.large_query_size,
        "sort": [{"build_start_time": {"order": "desc"}}],
        "_source": [
            "component", "component_repo", "component_repo_url", "component_ref",
            "version", "qualifier", "distribution_build_number", "distribution_build_url",
            "build_start_time", "rc", "rc_number", "component_category", "component_build_result"
        ],
        "query": {
            "bool": {
                "must": [
                    {"match_phrase": {"version": version}}
                ]
            }
        }
    }
    
    # Add build numbers filter
    if build_numbers:
        build_numbers_str = [str(bn) for bn in build_numbers]
        build_filter_clause = {"terms": {"distribution_build_number": build_numbers_str}}
        query_body["query"]["bool"]["must"].append(build_filter_clause)
    
    # Add component filter
    if components:
        component_clause = {"terms": {"component": components}}
        query_body["query"]["bool"]["must"].append(component_clause)
    
    # NOTE: status_filter is NOT applied at OpenSearch level to ensure proper deduplication
    # It will be applied after deduplication in the main handler
    
    return opensearch_request('POST', f'/{config.get_build_results_index_pattern()}/_search', query_body)


def query_release_readiness(version: str, components: Optional[List[str]] = None) -> Dict[str, Any]:
    """Query release readiness metrics with comprehensive field coverage."""
    query_body = {
        "size": config.large_query_size,
        "sort": [{"current_date": {"order": "desc"}}],
        "_source": [
            # Core identification fields
            "id", "component", "repository", "version", "release_version", "current_date",
            # Release state and branch information
            "release_state", "release_branch", "release_issue_exists", "release_issue",
            "release_notes", "version_increment", "release_owner_exists", "release_owners",
            # Issue and PR metrics
            "issues_open", "issues_closed", "pulls_open", "pulls_closed",
            # Autocut metrics
            "autocut_issues_open"
        ],
        "query": {
            "bool": {
                "must": [
                    {"match_phrase": {"version": version}}
                ]
            }
        }
    }
    
    # Use match_phrase for component filtering to avoid terms query issues
    if components:
        if len(components) == 1:
            query_body["query"]["bool"]["must"].append(
                {"match_phrase": {"component": components[0]}}
            )
        else:
            # Use should clause with multiple match_phrase for multiple components
            query_body["query"]["bool"]["must"].append({
                "bool": {
                    "should": [
                        {"match_phrase": {"component": comp}} for comp in components
                    ]
                }
            })
    
    return opensearch_request('POST', f'/{config.release_metrics_index}/_search', query_body)