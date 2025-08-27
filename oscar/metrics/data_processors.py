#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Data Processors for Metrics Lambda Functions.

This module provides data processing utilities including deduplication,
result extraction, and data transformation for the metrics system.

Functions:
    deduplicate_by_highest_build_number: Deduplicate by highest build number
    deduplicate_integration_test_results: Deduplicate integration test results
    deduplicate_release_results: Deduplicate release results
    extract_test_results: Extract test results from OpenSearch response
    extract_build_results: Extract build results from OpenSearch response
    extract_release_results: Extract release results from OpenSearch response
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def deduplicate_by_highest_build_number(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only highest build number for each (component, version, rc_number) combination.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        List of deduplicated results
    """
    groups = {}
    ungrouped = []
    
    for result in results:
        component = result.get('component')
        version = result.get('version')
        rc_number = result.get('rc_number')
        build_number = result.get('distribution_build_number')
        
        if component and version and rc_number is not None and build_number is not None:
            key = (component, version, rc_number)
            
            try:
                build_num = int(build_number)
                if key not in groups or int(groups[key].get('distribution_build_number', 0)) < build_num:
                    groups[key] = result
            except (ValueError, TypeError):
                logger.warning(f"Invalid build number for deduplication: {build_number}")
                ungrouped.append(result)
        else:
            ungrouped.append(result)
    
    return list(groups.values()) + ungrouped


def deduplicate_integration_test_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only most recent entry for each (component, version, rc_number, platform, architecture, distribution) combination.
    
    Integration test data often has multiple entries for the same component/RC due to
    different build times, retries, etc. We deduplicate by build_start_time to show
    only the most recent test result for each component configuration.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        List of deduplicated results
    """
    if not results:
        return results
    
    logger.info(f"DEDUP: Starting deduplication of {len(results)} integration test results")
    
    # Group by (component, version, rc_number, platform, architecture, distribution)
    groups = {}
    ungrouped = []
    
    for result in results:
        component = result.get('component')
        version = result.get('version')
        rc_number = result.get('rc_number')
        build_start_time = result.get('build_start_time')
        
        # Include platform/arch/distribution to keep legitimate different test configurations
        platform = result.get('platform')
        architecture = result.get('architecture') 
        distribution = result.get('distribution')
        
        if component and version and rc_number and platform and architecture and distribution is not None:
            key = (component, str(version), str(rc_number), str(platform), str(architecture), str(distribution))
            
            logger.debug(f"DEDUP: Processing {component} - key: {key}, build_time: {build_start_time}")
            
            if key not in groups:
                groups[key] = result
                logger.debug(f"DEDUP: Added new entry for {component}")
            else:
                # Compare by build_start_time (most recent wins)
                existing_time = groups[key].get('build_start_time')
                existing_status = groups[key].get('component_build_result')
                new_status = result.get('component_build_result')
                
                logger.debug(f"DEDUP: Comparing {component} - existing_time: {existing_time} ({existing_status}) vs new_time: {build_start_time} ({new_status})")
                
                if build_start_time and existing_time:
                    try:
                        # Convert to int for proper numeric comparison
                        new_time_int = int(build_start_time) if isinstance(build_start_time, str) else build_start_time
                        existing_time_int = int(existing_time) if isinstance(existing_time, str) else existing_time
                        
                        if new_time_int > existing_time_int:
                            logger.debug(f"DEDUP: Replacing {component} - newer time {new_time_int} > {existing_time_int}")
                            groups[key] = result
                        else:
                            logger.debug(f"DEDUP: Keeping existing {component} - older time {new_time_int} <= {existing_time_int}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"DEDUP: Error comparing times for {component}: {e}")
                        # If conversion fails, do string comparison
                        if build_start_time > existing_time:
                            groups[key] = result
                elif build_start_time and not existing_time:
                    # New result has timestamp, existing doesn't - prefer new
                    logger.debug(f"DEDUP: Replacing {component} - new has timestamp, existing doesn't")
                    groups[key] = result
                # If neither has timestamp or existing is newer, keep existing
        else:
            # Keep results without proper grouping keys
            logger.debug(f"DEDUP: Adding to ungrouped - missing fields: component={component}, version={version}, rc_number={rc_number}")
            ungrouped.append(result)
    
    deduplicated_results = list(groups.values()) + ungrouped
    logger.info(f"DEDUP: Deduplication complete: {len(results)} -> {len(deduplicated_results)} results")
    
    return deduplicated_results


def deduplicate_release_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only most recent entry for each (component, version) combination.
    
    Release readiness data does not contain RC/build numbers, only timestamps.
    We deduplicate by timestamp to avoid showing outdated release readiness states
    when newer evaluations exist for the same component/version.
    """
    if not results:
        return results
    
    # Group by (component, version)
    groups = {}
    ungrouped = []
    
    for result in results:
        component = result.get('component')
        version = result.get('version')
        # Use current_date instead of timestamp for release data
        timestamp = result.get('current_date') or result.get('timestamp')
        
        # Only group if we have required fields
        if component and version:
            key = (component, str(version))
            # Use timestamp for comparison, fallback to keeping first if no timestamp
            if key not in groups:
                groups[key] = result
            elif timestamp:
                existing_timestamp = groups[key].get('current_date') or groups[key].get('timestamp')
                if not existing_timestamp or timestamp > existing_timestamp:
                    groups[key] = result
        else:
            # Keep results without proper grouping keys
            ungrouped.append(result)
    
    deduplicated_results = list(groups.values()) + ungrouped
    
    return deduplicated_results


def extract_test_results(opensearch_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract comprehensive test result information based on real data structure."""
    logger.info(f"EXTRACT_RESULTS: Starting result extraction")
    results = []
    hits = opensearch_result.get('hits', {}).get('hits', [])
    logger.info(f"EXTRACT_RESULTS: Processing {len(hits)} hits")
    
    for hit in hits:
        source = hit['_source']
        
        # Determine overall test status based on with_security and without_security results
        with_security = source.get('with_security', '')
        without_security = source.get('without_security', '')
        component_build_result = source.get('component_build_result', '')
        
        if component_build_result != 'failed' and with_security == 'pass' and without_security == 'pass':
            overall_status = 'passed'
        else: overall_status = 'failed'
        
        results.append({
            'component': source.get('component'),
            'status': overall_status,
            'component_build_result': component_build_result,
            'build_number': source.get('distribution_build_number'),
            'integ_test_build_number': source.get('integ_test_build_number'),
            'rc_number': source.get('rc_number'),
            'version': source.get('version'),
            'platform': source.get('platform'),
            'architecture': source.get('architecture'),
            'distribution': source.get('distribution'),
            'category': source.get('component_category'),
            'test_report': source.get('test_report_manifest_yml'),
            'build_start_time': source.get('build_start_time'),
            # Security test details
            'with_security': with_security,
            'without_security': without_security,
        })
    
    logger.info(f"EXTRACT_RESULTS: Extracted {len(results)} results, about to deduplicate")
    deduplicated = deduplicate_integration_test_results(results)
    logger.info(f"EXTRACT_RESULTS: Deduplication complete, returning {len(deduplicated)} results")
    return deduplicated


def extract_build_results(opensearch_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract build result information."""
    results = []
    hits = opensearch_result.get('hits', {}).get('hits', [])
    
    for hit in hits:
        source = hit['_source']
        results.append({
            'component': source.get('component'),
            'component_repo': source.get('component_repo'),
            'component_repo_url': source.get('component_repo_url'),
            'version': source.get('version'),
            'qualifier': source.get('qualifier'),
            'distribution_build_number': source.get('distribution_build_number'),
            'distribution_build_url': source.get('distribution_build_url'),
            'build_start_time': source.get('build_start_time'),
            'rc_number': source.get('rc_number'),
            'component_category': source.get('component_category'),
            'component_build_result': source.get('component_build_result'),
        })
    
    return deduplicate_by_highest_build_number(results)


def extract_release_results(opensearch_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract comprehensive release readiness information."""
    results = []
    hits = opensearch_result.get('hits', {}).get('hits', [])
    
    for hit in hits:
        source = hit['_source']
        
        # Calculate enhanced readiness score based on all available metrics
        readiness_score = 0
        
        # Core release readiness checks
        if source.get('release_issue_exists'):
            readiness_score += 1
        if source.get('release_notes'):
            readiness_score += 1
        if source.get('version_increment'):
            readiness_score += 1
        if source.get('release_branch'):
            readiness_score += 1
        if source.get('release_owner_exists'):
            readiness_score += 1        
            
        # Additional quality checks
        issues_open = source.get('issues_open', 0)
        pulls_open = source.get('pulls_open', 0)
        autocut_issues_open = source.get('autocut_issues_open', 0)
        
        component = source.get('component')
        release_notes = source.get('release_notes')
        current_date = source.get('current_date')
        
        results.append({
            # Core identification
            'id': source.get('id'),
            'component': component,
            'repository': source.get('repository'),
            'version': source.get('version'),
            'timestamp': current_date,
            
            # Release state information
            'release_state': source.get('release_state'),
            'release_branch': source.get('release_branch'),
            'release_issue_exists': source.get('release_issue_exists'),
            'release_issue': source.get('release_issue'),
            'release_notes': release_notes,
            'version_increment': source.get('version_increment'),
            'release_owner_exists': source.get('release_owner_exists'),
            'release_owners': source.get('release_owners', []),
            
            # Issue and PR metrics
            'issues_open': issues_open,
            'issues_closed': source.get('issues_closed', 0),
            'pulls_open': pulls_open,
            'pulls_closed': source.get('pulls_closed', 0),
            'autocut_issues_open': autocut_issues_open,
            
            # Calculated readiness metrics
            'readiness_score': round(readiness_score, 1),            
            # Quality indicators
            'has_open_issues': issues_open > 0,
            'has_open_pulls': pulls_open > 0,
            'has_autocut_issues': autocut_issues_open > 0,
        })
    
    # Apply deduplication to avoid duplicate component entries
    return deduplicate_release_results(results)