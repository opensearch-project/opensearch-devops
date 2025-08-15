#!/usr/bin/env python3

import json
import logging
import os
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

logger = logging.getLogger(__name__)

def get_opensearch_session():
    """Get boto3 session with assumed cross-account role."""
    sts_client = boto3.client('sts')
    response = sts_client.assume_role(
        RoleArn='arn:aws:iam::979020455945:role/OpenSearchOscarAccessRole',
        RoleSessionName='oscar-index-explorer'
    )
    
    return boto3.Session(
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken']
    )

def opensearch_request(method, path, body=None):
    """Make signed HTTP request to OpenSearch."""
    opensearch_host = os.getenv('OPENSEARCH_HOST', '').replace('https://', '')
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
    SigV4Auth(credentials, 'es', 'us-east-1').add_auth(request)
    
    # Make the request
    response = requests.request(
        method=request.method,
        url=request.url,
        data=request.body,
        headers=dict(request.headers),
        timeout=30
    )
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        raise Exception(f'OpenSearch request failed: {response.status_code} - {response.text}')

def lambda_handler(event, context):
    """Index exploration Lambda handler."""
    try:
        logger.info("Index explorer started")
        
        function_name = event.get('function', 'list_indices')
        
        if function_name == 'list_indices':
            result = list_all_indices()
        elif function_name == 'explore_build_indices':
            result = explore_build_indices()
        elif function_name == 'get_index_mapping':
            index_name = event.get('index_name', 'opensearch_release_metrics')
            result = get_index_mapping(index_name)
        elif function_name == 'sample_documents':
            index_name = event.get('index_name', 'opensearch_release_metrics')
            result = sample_documents(index_name)
        elif function_name == 'cluster_info':
            result = get_cluster_info()
        else:
            result = {'error': f'Unknown function: {function_name}'}
        
        return create_response(result)
        
    except Exception as e:
        logger.error(f"Index explorer error: {e}", exc_info=True)
        return create_response({'error': str(e), 'type': 'explorer_error'})

def list_all_indices():
    """List all indices in the OpenSearch cluster."""
    try:
        indices = opensearch_request('GET', '/_cat/indices?format=json')
        
        # Sort by document count
        sorted_indices = sorted(indices, key=lambda x: int(x.get('docs.count', '0')), reverse=True)
        
        return {
            'status': 'success',
            'total_indices': len(indices),
            'indices': [
                {
                    'name': idx.get('index'),
                    'doc_count': idx.get('docs.count'),
                    'store_size': idx.get('store.size'),
                    'health': idx.get('health'),
                    'status': idx.get('status')
                }
                for idx in sorted_indices[:20]  # Top 20 by document count
            ]
        }
        
    except Exception as e:
        return {'error': str(e), 'type': 'list_indices_error'}

def explore_build_indices():
    """Explore build-related indices specifically."""
    try:
        indices = opensearch_request('GET', '/_cat/indices?format=json')
        
        # Filter for build/test/release related indices
        keywords = ['build', 'test', 'release', 'deploy', 'metric', 'opensearch']
        build_indices = [
            idx for idx in indices 
            if any(keyword in idx.get('index', '').lower() for keyword in keywords)
        ]
        
        detailed_info = []
        for idx in build_indices[:10]:  # Limit to 10 indices
            index_name = idx.get('index')
            try:
                # Get mapping
                mapping = opensearch_request('GET', f'/{index_name}/_mapping')
                
                # Get sample documents
                sample = opensearch_request('POST', f'/{index_name}/_search', {
                    "size": 3,
                    "query": {"match_all": {}}
                })
                
                # Extract field information
                properties = mapping.get(index_name, {}).get('mappings', {}).get('properties', {})
                field_info = {
                    field_name: field_config.get('type', 'unknown')
                    for field_name, field_config in properties.items()
                }
                
                detailed_info.append({
                    'index_name': index_name,
                    'doc_count': idx.get('docs.count'),
                    'store_size': idx.get('store.size'),
                    'field_count': len(field_info),
                    'field_types': field_info,
                    'sample_documents': [
                        hit.get('_source', {})
                        for hit in sample.get('hits', {}).get('hits', [])
                    ]
                })
                
            except Exception as e:
                detailed_info.append({
                    'index_name': index_name,
                    'error': str(e)
                })
        
        return {
            'status': 'success',
            'build_indices_found': len(build_indices),
            'detailed_info': detailed_info
        }
        
    except Exception as e:
        return {'error': str(e), 'type': 'explore_build_error'}

def get_index_mapping(index_name):
    """Get detailed mapping for a specific index."""
    try:
        mapping = opensearch_request('GET', f'/{index_name}/_mapping')
        
        # Extract properties
        properties = mapping.get(index_name, {}).get('mappings', {}).get('properties', {})
        
        field_details = {}
        for field_name, field_config in properties.items():
            field_details[field_name] = {
                'type': field_config.get('type', 'unknown'),
                'properties': field_config.get('properties', {}),
                'format': field_config.get('format'),
                'analyzer': field_config.get('analyzer')
            }
        
        return {
            'status': 'success',
            'index_name': index_name,
            'field_count': len(field_details),
            'field_details': field_details
        }
        
    except Exception as e:
        return {'error': str(e), 'type': 'mapping_error'}

def sample_documents(index_name, size=5):
    """Get sample documents from an index."""
    try:
        # Get recent documents
        sample = opensearch_request('POST', f'/{index_name}/_search', {
            "size": size,
            "query": {"match_all": {}},
            "sort": [{"_score": {"order": "desc"}}]
        })
        
        hits = sample.get('hits', {})
        documents = hits.get('hits', [])
        
        return {
            'status': 'success',
            'index_name': index_name,
            'total_documents': hits.get('total', {}).get('value', 0),
            'sample_size': len(documents),
            'documents': [
                {
                    'id': doc.get('_id'),
                    'source': doc.get('_source', {}),
                    'score': doc.get('_score')
                }
                for doc in documents
            ]
        }
        
    except Exception as e:
        return {'error': str(e), 'type': 'sample_error'}

def get_cluster_info():
    """Get OpenSearch cluster information."""
    try:
        # Cluster health
        health = opensearch_request('GET', '/_cluster/health')
        
        # Cluster stats
        stats = opensearch_request('GET', '/_cluster/stats')
        
        # Node info
        nodes = opensearch_request('GET', '/_nodes/stats')
        
        return {
            'status': 'success',
            'cluster_health': {
                'status': health.get('status'),
                'cluster_name': health.get('cluster_name'),
                'number_of_nodes': health.get('number_of_nodes'),
                'active_primary_shards': health.get('active_primary_shards'),
                'active_shards': health.get('active_shards')
            },
            'cluster_stats': {
                'indices_count': stats.get('indices', {}).get('count', 0),
                'docs_count': stats.get('indices', {}).get('docs', {}).get('count', 0),
                'store_size': stats.get('indices', {}).get('store', {}).get('size_in_bytes', 0)
            },
            'node_count': len(nodes.get('nodes', {}))
        }
        
    except Exception as e:
        return {'error': str(e), 'type': 'cluster_info_error'}

def create_response(result):
    """Create Bedrock-compatible response."""
    return {
        'response': {
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps(result, indent=2, default=str)
                    }
                }
            }
        }
    }