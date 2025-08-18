#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
AWS Utilities for Metrics Lambda Functions.

This module provides AWS-related utilities including session management,
cross-account role assumption, and OpenSearch request handling.

Functions:
    get_opensearch_session: Get boto3 session with assumed cross-account role
    opensearch_request: Make signed HTTP request to OpenSearch
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from config import config

logger = logging.getLogger(__name__)


def get_opensearch_session():
    """Get boto3 session with assumed cross-account role."""
    sts_client = boto3.client('sts')
    response = sts_client.assume_role(
        RoleArn=config.metrics_cross_account_role_arn,
        RoleSessionName='oscar-metrics-session'
    )
    
    return boto3.Session(
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken']
    )


def opensearch_request(method, path, body=None):
    """Make signed HTTP request to OpenSearch."""
    opensearch_host = config.get_opensearch_host_clean()
    if not opensearch_host:
        raise ValueError("OPENSEARCH_HOST not configured")
    
    url = f'https://{opensearch_host}{path}'
    session = get_opensearch_session()
    
    # Create signed request
    request = AWSRequest(
        method=method,
        url=url,
        data=json.dumps(body) if body else None,
        headers={'Content-Type': 'application/json'} if body else {}
    )
    
    # Sign the request
    credentials = session.get_credentials()
    SigV4Auth(credentials, config.opensearch_service, config.opensearch_region).add_auth(request)
    
    # Make the request
    response = requests.request(
        method=request.method,
        url=request.url,
        data=request.body,
        headers=dict(request.headers),
        timeout=config.opensearch_request_timeout
    )
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        raise Exception(f'OpenSearch request failed: {response.status_code} - {response.text}')