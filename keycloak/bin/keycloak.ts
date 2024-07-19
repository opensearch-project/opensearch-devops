/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { App } from 'aws-cdk-lib';
import 'source-map-support/register';
import { AllStacks } from '../lib/all-stacks';

const app = new App();
new AllStacks(app, 'KeycloakStack', {});
