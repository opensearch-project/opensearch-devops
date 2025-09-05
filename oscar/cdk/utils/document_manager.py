#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Document management utilities for OSCAR Knowledge Base.

This module provides utilities for automated document ingestion from cdk/knowledge_docs/,
document preprocessing, chunking, and synchronization with the Knowledge Base.
"""

import os
import re
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentManager:
    """
    Manages document ingestion and preprocessing for OSCAR Knowledge Base.
    
    This class handles automated document ingestion from the knowledge_docs directory,
    preprocessing documents for optimal chunking, and synchronizing with S3 and
    the Bedrock Knowledge Base.
    """
    
    def __init__(
        self, 
        bucket_name: str, 
        knowledge_base_id: str,
        data_source_id: str,
        region: str = "us-east-1"
    ):
        """
        Initialize the document manager.
        
        Args:
            bucket_name: Name of the S3 bucket for document storage
            knowledge_base_id: ID of the Bedrock Knowledge Base
            data_source_id: ID of the Knowledge Base data source
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.knowledge_base_id = knowledge_base_id
        self.data_source_id = data_source_id
        self.region = region
        
        # Initialize AWS clients
        try:
            self.s3_client = boto3.client('s3', region_name=region)
            self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure your credentials.")
            raise
        
        # Document processing configuration
        self.supported_extensions = {'.md', '.txt', '.rst', '.json'}
        self.docs_prefix = "docs/"
        self.metadata_file = "document_metadata.json"
        
        # Chunking configuration
        self.max_chunk_size = 300  # tokens
        self.chunk_overlap = 20  # percentage
    
    def ingest_documents_from_directory(self, docs_directory: str) -> Dict[str, str]:
        """
        Ingest all documents from the specified directory to S3.
        
        Args:
            docs_directory: Path to the directory containing documents
            
        Returns:
            Dictionary mapping local file paths to S3 keys
            
        Raises:
            FileNotFoundError: If the docs directory doesn't exist
            ClientError: If S3 operations fail
        """
        docs_path = Path(docs_directory)
        if not docs_path.exists():
            raise FileNotFoundError(f"Documents directory not found: {docs_directory}")
        
        logger.info(f"Starting document ingestion from {docs_directory}")
        
        uploaded_files = {}
        processed_count = 0
        skipped_count = 0
        
        # Walk through all files in the directory
        for file_path in docs_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                try:
                    # Process and upload the document
                    s3_key = self._upload_document(file_path)
                    if s3_key:
                        uploaded_files[str(file_path)] = s3_key
                        processed_count += 1
                        logger.info(f"Uploaded: {file_path.name} -> {s3_key}")
                    else:
                        skipped_count += 1
                        logger.info(f"Skipped (no changes): {file_path.name}")
                        
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {str(e)}")
                    skipped_count += 1
        
        logger.info(f"Document ingestion completed. Processed: {processed_count}, Skipped: {skipped_count}")
        
        # Trigger Knowledge Base sync if documents were uploaded
        if processed_count > 0:
            self._trigger_knowledge_base_sync()
        
        return uploaded_files
    
    def _upload_document(self, file_path: Path) -> Optional[str]:
        """
        Upload a single document to S3 with preprocessing.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            S3 key if uploaded, None if skipped
        """
        try:
            # Read and preprocess the document
            content = self._preprocess_document(file_path)
            if not content.strip():
                logger.warning(f"Document is empty after preprocessing: {file_path}")
                return None
            
            # Generate S3 key
            relative_path = file_path.name
            s3_key = f"{self.docs_prefix}{relative_path}"
            
            # Check if document has changed (using content hash)
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            if self._document_unchanged(s3_key, content_hash):
                return None
            
            # Create metadata
            metadata = self._create_document_metadata(file_path, content_hash)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content.encode('utf-8'),
                ContentType='text/plain',
                Metadata=metadata
            )
            
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {str(e)}")
            raise
    
    def _preprocess_document(self, file_path: Path) -> str:
        """
        Preprocess document content for optimal chunking and indexing.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Preprocessed document content
        """
        try:
            # Read the file with UTF-8 encoding
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Basic preprocessing
            content = self._clean_markdown(content)
            content = self._normalize_whitespace(content)
            content = self._add_document_metadata_header(file_path, content)
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to preprocess {file_path}: {str(e)}")
            raise
    
    def _clean_markdown(self, content: str) -> str:
        """
        Clean markdown content for better processing.
        
        Args:
            content: Raw markdown content
            
        Returns:
            Cleaned markdown content
        """
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Clean up code blocks (preserve but normalize)
        content = re.sub(r'```(\w+)?\n', r'```\1\n', content)
        
        # Normalize headers
        content = re.sub(r'^#{1,6}\s*', lambda m: '#' * len(m.group().strip()) + ' ', content, flags=re.MULTILINE)
        
        # Remove HTML comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        return content
    
    def _normalize_whitespace(self, content: str) -> str:
        """
        Normalize whitespace in document content.
        
        Args:
            content: Document content
            
        Returns:
            Content with normalized whitespace
        """
        # Replace multiple spaces with single space
        content = re.sub(r' +', ' ', content)
        
        # Replace tabs with spaces
        content = content.replace('\t', '    ')
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove trailing whitespace from lines
        content = '\n'.join(line.rstrip() for line in content.split('\n'))
        
        return content.strip()
    
    def _add_document_metadata_header(self, file_path: Path, content: str) -> str:
        """
        Add metadata header to document for better context.
        
        Args:
            file_path: Path to the document file
            content: Document content
            
        Returns:
            Content with metadata header
        """
        # Create metadata header
        header = f"""---
Document: {file_path.name}
Type: {file_path.suffix[1:].upper() if file_path.suffix else 'TEXT'}
Source: OSCAR Knowledge Base
---

"""
        
        return header + content
    
    def _create_document_metadata(self, file_path: Path, content_hash: str) -> Dict[str, str]:
        """
        Create metadata for S3 object.
        
        Args:
            file_path: Path to the document file
            content_hash: MD5 hash of the content
            
        Returns:
            Metadata dictionary
        """
        return {
            'document-name': file_path.name,
            'document-type': file_path.suffix[1:] if file_path.suffix else 'txt',
            'content-hash': content_hash,
            'source': 'oscar-knowledge-docs',
            'processed-by': 'oscar-document-manager'
        }
    
    def _document_unchanged(self, s3_key: str, content_hash: str) -> bool:
        """
        Check if document content has changed since last upload.
        
        Args:
            s3_key: S3 key for the document
            content_hash: Current content hash
            
        Returns:
            True if document is unchanged, False otherwise
        """
        try:
            # Get object metadata
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Compare content hash
            existing_hash = response.get('Metadata', {}).get('content-hash')
            return existing_hash == content_hash
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Object doesn't exist, so it's changed (new)
                return False
            else:
                logger.warning(f"Failed to check document status for {s3_key}: {str(e)}")
                return False
    
    def _trigger_knowledge_base_sync(self) -> None:
        """
        Trigger Knowledge Base synchronization after document updates.
        """
        try:
            logger.info("Triggering Knowledge Base synchronization...")
            
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.data_source_id,
                description="Automated sync triggered by document manager"
            )
            
            job_id = response['ingestionJob']['ingestionJobId']
            logger.info(f"Knowledge Base sync started. Job ID: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger Knowledge Base sync: {str(e)}")
            raise
    
    def get_sync_status(self) -> Dict[str, str]:
        """
        Get the status of the latest Knowledge Base synchronization.
        
        Returns:
            Dictionary with sync status information
        """
        try:
            response = self.bedrock_agent_client.list_ingestion_jobs(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.data_source_id,
                maxResults=1
            )
            
            if response['ingestionJobSummaries']:
                latest_job = response['ingestionJobSummaries'][0]
                return {
                    'job_id': latest_job['ingestionJobId'],
                    'status': latest_job['status'],
                    'started_at': str(latest_job['startedAt']),
                    'updated_at': str(latest_job.get('updatedAt', 'N/A'))
                }
            else:
                return {'status': 'No sync jobs found'}
                
        except Exception as e:
            logger.error(f"Failed to get sync status: {str(e)}")
            return {'status': 'Error', 'error': str(e)}
    
    def list_documents(self) -> List[Dict[str, str]]:
        """
        List all documents in the Knowledge Base S3 bucket.
        
        Returns:
            List of document information dictionaries
        """
        try:
            documents = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.docs_prefix):
                for obj in page.get('Contents', []):
                    # Get object metadata
                    try:
                        metadata_response = self.s3_client.head_object(
                            Bucket=self.bucket_name,
                            Key=obj['Key']
                        )
                        metadata = metadata_response.get('Metadata', {})
                        
                        documents.append({
                            'key': obj['Key'],
                            'name': metadata.get('document-name', obj['Key'].split('/')[-1]),
                            'type': metadata.get('document-type', 'unknown'),
                            'size': obj['Size'],
                            'last_modified': str(obj['LastModified']),
                            'content_hash': metadata.get('content-hash', 'unknown')
                        })
                    except Exception as e:
                        logger.warning(f"Failed to get metadata for {obj['Key']}: {str(e)}")
                        documents.append({
                            'key': obj['Key'],
                            'name': obj['Key'].split('/')[-1],
                            'type': 'unknown',
                            'size': obj['Size'],
                            'last_modified': str(obj['LastModified']),
                            'content_hash': 'unknown'
                        })
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise


def main():
    """
    Main function for command-line usage of the document manager.
    """
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="OSCAR Knowledge Base Document Manager")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--kb-id", required=True, help="Knowledge Base ID")
    parser.add_argument("--ds-id", required=True, help="Data Source ID")
    parser.add_argument("--docs-dir", default="cdk/knowledge_docs", help="Documents directory")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--action", choices=["ingest", "status", "list"], default="ingest", 
                       help="Action to perform")
    
    args = parser.parse_args()
    
    # Initialize document manager
    doc_manager = DocumentManager(
        bucket_name=args.bucket,
        knowledge_base_id=args.kb_id,
        data_source_id=args.ds_id,
        region=args.region
    )
    
    try:
        if args.action == "ingest":
            # Ingest documents
            result = doc_manager.ingest_documents_from_directory(args.docs_dir)
            print(f"Ingested {len(result)} documents")
            print(json.dumps(result, indent=2))
            
        elif args.action == "status":
            # Get sync status
            status = doc_manager.get_sync_status()
            print("Knowledge Base Sync Status:")
            print(json.dumps(status, indent=2))
            
        elif args.action == "list":
            # List documents
            documents = doc_manager.list_documents()
            print(f"Found {len(documents)} documents:")
            print(json.dumps(documents, indent=2))
            
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())