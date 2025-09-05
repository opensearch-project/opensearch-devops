#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
"""
Dynamic Lambda Asset Management for OSCAR CDK.

This module handles on-demand generation of Lambda deployment packages,
eliminating the need for pre-built lambda_assets directory.
"""

import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class DynamicLambdaAssets:
    """Manages dynamic generation of Lambda deployment assets."""
    
    def __init__(self, cdk_dir: str):
        """Initialize with CDK directory path."""
        self.cdk_dir = Path(cdk_dir)
        self.assets_dir = self.cdk_dir / "lambda_assets"
        self.prepare_script = self.cdk_dir / "prepare_lambda_assets.sh"
        self._assets_prepared = False
    
    def ensure_assets_prepared(self) -> bool:
        """
        Ensure Lambda assets are prepared for deployment.
        
        Returns:
            bool: True if assets were successfully prepared
        """
        if self.assets_dir.exists() and self._assets_prepared:
            logger.info("Lambda assets already prepared")
            return True
        
        # Check if assets directory exists with expected content
        if self.assets_dir.exists():
            expected_assets = ["oscar-agent", "oscar-communication-handler", "jenkins", "metrics"]
            existing_assets = [d.name for d in self.assets_dir.iterdir() if d.is_dir()]
            if all(asset in existing_assets for asset in expected_assets):
                logger.info("Lambda assets directory already exists with expected content")
                self._assets_prepared = True
                return True
        
        logger.info("Preparing Lambda assets dynamically...")
        
        try:
            # Check if prepare script exists
            if not self.prepare_script.exists():
                raise FileNotFoundError(f"Asset preparation script not found: {self.prepare_script}")
            
            # Make script executable
            os.chmod(self.prepare_script, 0o755)
            
            # Run the preparation script
            result = subprocess.run(
                [str(self.prepare_script)],
                cwd=self.cdk_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("Asset preparation completed successfully")
            logger.debug(f"Preparation output: {result.stdout}")
            
            # Verify assets were created
            if not self.assets_dir.exists():
                raise RuntimeError("Assets directory was not created")
            
            # Verify expected asset directories exist
            expected_assets = ["oscar-agent", "oscar-communication-handler", "jenkins", "metrics"]
            for asset in expected_assets:
                asset_path = self.assets_dir / asset
                if not asset_path.exists():
                    logger.warning(f"Expected asset directory not found: {asset}")
            
            self._assets_prepared = True
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Asset preparation failed: {e}")
            logger.error(f"Script output: {e.stdout}")
            logger.error(f"Script errors: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during asset preparation: {e}")
            return False
    
    def get_asset_path(self, asset_name: str) -> str:
        """
        Get the path to a specific Lambda asset.
        
        Args:
            asset_name: Name of the asset (e.g., 'oscar-agent', 'jenkins')
            
        Returns:
            str: Path to the asset directory
            
        Raises:
            RuntimeError: If assets are not prepared or asset doesn't exist
        """
        if not self.ensure_assets_prepared():
            raise RuntimeError("Failed to prepare Lambda assets")
        
        asset_path = self.assets_dir / asset_name
        if not asset_path.exists():
            raise RuntimeError(f"Asset not found: {asset_name}")
        
        return str(asset_path)
    
    def cleanup_assets(self) -> None:
        """Clean up generated assets to save disk space."""
        if self.assets_dir.exists():
            logger.info("Cleaning up Lambda assets...")
            shutil.rmtree(self.assets_dir)
            self._assets_prepared = False
            logger.info("Lambda assets cleaned up")
    
    def get_asset_size(self, asset_name: Optional[str] = None) -> str:
        """
        Get the size of assets.
        
        Args:
            asset_name: Specific asset name, or None for total size
            
        Returns:
            str: Human-readable size string
        """
        try:
            if asset_name:
                path = self.assets_dir / asset_name
            else:
                path = self.assets_dir
            
            if not path.exists():
                return "0B"
            
            result = subprocess.run(
                ["du", "-sh", str(path)],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.split()[0]
        except Exception:
            return "unknown"

# Global instance for CDK stacks to use
_assets_manager: Optional[DynamicLambdaAssets] = None

def get_assets_manager() -> DynamicLambdaAssets:
    """Get the global assets manager instance."""
    global _assets_manager
    if _assets_manager is None:
        # Determine CDK directory (assuming this file is in cdk/utils/)
        cdk_dir = Path(__file__).parent.parent
        _assets_manager = DynamicLambdaAssets(str(cdk_dir))
    return _assets_manager

def prepare_lambda_assets() -> bool:
    """Convenience function to prepare Lambda assets."""
    return get_assets_manager().ensure_assets_prepared()

def get_lambda_asset_path(asset_name: str) -> str:
    """Convenience function to get Lambda asset path."""
    return get_assets_manager().get_asset_path(asset_name)

def cleanup_lambda_assets() -> None:
    """Convenience function to cleanup Lambda assets."""
    get_assets_manager().cleanup_assets()