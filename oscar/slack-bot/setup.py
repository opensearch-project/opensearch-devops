#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Setup script for OSCAR Slack Bot with security checks.
"""

from setuptools import setup, find_packages
import sys
import subprocess

# Read requirements from file
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Security constants
URLLIB3_MIN_VERSION = "2.5.0"

def check_urllib3_version():
    """Check if urllib3 is at the secure version."""
    try:
        import urllib3
        current_version = urllib3.__version__
        print(f"Current urllib3 version: {current_version}")
        
        if current_version != URLLIB3_MIN_VERSION:
            print(f"WARNING: urllib3 version {current_version} does not match required version {URLLIB3_MIN_VERSION}")
            print("Attempting to fix by reinstalling the correct version...")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', f'urllib3=={URLLIB3_MIN_VERSION}', '--force-reinstall'
            ])
            print(f"urllib3 version {URLLIB3_MIN_VERSION} installed successfully")
        else:
            print(f"urllib3 version {URLLIB3_MIN_VERSION} is correctly installed")
            
    except ImportError:
        print("urllib3 is not installed. It will be installed during setup.")

# Check urllib3 version before setup
if 'install' in sys.argv or 'develop' in sys.argv:
    check_urllib3_version()

setup(
    name="oscar-slack-bot",
    version="0.1.0",
    description="OpenSearch Conversational Automation for Releases Slack Bot",
    author="OpenSearch Contributors",
    author_email="opensearch-infra@amazon.com",
    url="https://github.com/opensearch-project/opensearch-chatbot",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)