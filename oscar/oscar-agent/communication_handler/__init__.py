#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Communication Handler package for OSCAR Agent.

This package provides modular communication handling functionality.
"""

from communication_handler.lambda_handler import lambda_handler

__all__ = ['lambda_handler']