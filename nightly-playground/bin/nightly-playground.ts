#!/usr/bin/env node

/* Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0

The OpenSearch Contributors require contributions made to
this file be licensed under the Apache-2.0 license or a
compatible open source license. */

import { App } from 'aws-cdk-lib';
import { NightlyPlaygroundStack } from '../lib/nightly-playground-stack';

const app = new App();
const region = app.node.tryGetContext('region') ?? process.env.CDK_DEFAULT_REGION;
const account = app.node.tryGetContext('account') ?? process.env.CDK_DEFAULT_ACCOUNT;

const nighlty = new NightlyPlaygroundStack(app, {
  env: { account, region },
});
