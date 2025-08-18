#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Summary Generators for Metrics Lambda Functions.

This module provides summary generation utilities for different types of
metrics data, creating human-readable summaries for the agent responses.

Functions:
    generate_integration_summary: Generate summary for integration test results
    generate_build_summary: Generate summary for build results
    generate_release_summary: Generate summary for release results
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def generate_integration_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary for integration test results.
    
    Args:
        results: List of integration test results
        
    Returns:
        Dictionary containing summary statistics
    """
    all_results = []
    for result in results:
        # Assuming that component build status fails only when at least one of with security and without security fail
        status = result.get('component_build_result', 'unknown')
        all_results.append(status)
    
    passed_count = all_results.count('passed')
    failed_count = all_results.count('failed')
    total_count = len(all_results)
    
    return {
        'total_tests': total_count,
        'passed_tests': passed_count,
        'failed_tests': failed_count,
        'success_rate': round((passed_count / total_count * 100), 2) if total_count > 0 else 0,
        'status_breakdown': {
            'passed': passed_count,
            'failed': failed_count,
            'other': total_count - passed_count - failed_count
        }
    }


def generate_build_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary for build results.
    
    Args:
        results: List of build results
        
    Returns:
        Dictionary containing summary statistics
    """
    all_results = []
    components = set()
    
    for result in results:
        status = result.get('component_build_result', 'unknown')
        component = result.get('component')
        all_results.append(status)
        if component:
            components.add(component)
    
    passed_count = all_results.count('passed')
    failed_count = all_results.count('failed')
    total_count = len(all_results)
    
    return {
        'total_builds': total_count,
        'unique_components': len(components),
        'passed_builds': passed_count,
        'failed_builds': failed_count,
        'success_rate': round((passed_count / total_count * 100), 2) if total_count > 0 else 0,
        'status_breakdown': {
            'passed': passed_count,
            'failed': failed_count,
            'other/unknown': total_count - passed_count - failed_count
        }
    }


def generate_release_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate comprehensive summary for release results.
    
    Args:
        results: List of release results
        
    Returns:
        Dictionary containing summary statistics
    """
    all_results = []
    components = set()
    release_states = []
    
    # Status counters based on actual data structure
    status_counters = {
        'release_issue_exists': {'true': 0, 'false': 0},
        'release_notes': {'true': 0, 'false': 0},
        'version_increment': {'true': 0, 'false': 0},
        'release_owner_exists': {'true': 0, 'false': 0},
        'release_branch': {'true': 0, 'false': 0}
    }
    
    # Detailed component lists for release notes
    components_with_release_notes = []
    components_without_release_notes = []
    
    # Numeric counters
    total_issues_open = 0
    total_issues_closed = 0
    total_pulls_open = 0
    total_pulls_closed = 0
    total_autocut_issues = 0
    
    for result in results:
        component = result.get('component')
        release_state = result.get('release_state', 'unknown')
        release_notes = result.get('release_notes')
        
        if component:
            components.add(component)
            
            # Track release notes completion by component
            if release_notes is True:
                components_with_release_notes.append(component)
            else:
                components_without_release_notes.append(component)
        
        release_states.append(release_state)
        all_results.append(result)
        
        # Count boolean status fields
        for status_field in status_counters:
            status_value = result.get(status_field)
            if status_value is True:
                status_counters[status_field]['true'] += 1
            elif status_value is False:
                status_counters[status_field]['false'] += 1
        
        # Sum numeric fields
        total_issues_open += result.get('issues_open', 0)
        total_issues_closed += result.get('issues_closed', 0)
        total_pulls_open += result.get('pulls_open', 0)
        total_pulls_closed += result.get('pulls_closed', 0)
        total_autocut_issues += result.get('autocut_issues_open', 0)
    
    # Calculate release state statistics
    open_count = release_states.count('open')
    closed_count = release_states.count('closed')
    total_count = len(release_states)
    
    return {
        'total_components': total_count,
        'unique_components': len(components),
        'open_releases': open_count,
        'closed_releases': closed_count,
        'completion_rate': round((closed_count / total_count * 100), 2) if total_count > 0 else 0,
        'release_state_breakdown': {
            'open': open_count,
            'closed': closed_count,
            'other': total_count - open_count - closed_count
        },
        'status_breakdown': status_counters,
        'release_notes_summary': {
            'completed_count': len(components_with_release_notes),
            'missing_count': len(components_without_release_notes),
            'completion_percentage': round((len(components_with_release_notes) / len(components) * 100), 2) if len(components) > 0 else 0,
            'components_with_release_notes': sorted(components_with_release_notes),
            'components_without_release_notes': sorted(components_without_release_notes)
        },
        'totals': {
            'issues_open': total_issues_open,
            'issues_closed': total_issues_closed,
            'pulls_open': total_pulls_open,
            'pulls_closed': total_pulls_closed,
            'autocut_issues_open': total_autocut_issues
        }
    }