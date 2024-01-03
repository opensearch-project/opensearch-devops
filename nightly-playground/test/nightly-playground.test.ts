/* Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0

The OpenSearch Contributors require contributions made to
this file be licensed under the Apache-2.0 license or a
compatible open source license. */

import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { NightlyPlaygroundStack } from '../lib/nightly-playground-stack';

test('Ensure security is always enabled', () => {
  const app = new App({
    context: {
      distVersion: '2.3.0',
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
    },
  });

  // WHEN
  const nightlyStack = new NightlyPlaygroundStack(app, '2x', {
    env: { account: 'test-account', region: 'us-east-1' },
  });

  // THEN
  expect(nightlyStack.stacks).toHaveLength(2);
  const infraStack = nightlyStack.stacks.filter((s) => s.stackName === 'infraStack-2x')[0];
  const infraTemplate = Template.fromStack(infraStack);

  infraTemplate.hasResourceProperties('AWS::ElasticLoadBalancingV2::Listener', {
    Port: 443,
    Protocol: 'TCP',
  });
});

test('Throw an error for missing distVersion', () => {
  const app = new App({
    context: {
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
    },
  });
  // WHEN
  try {
  // WHEN
    const nightlyStack = new NightlyPlaygroundStack(app, '2x', {
      env: { account: 'test-account', region: 'us-east-1' },
    });

    // eslint-disable-next-line no-undef
    fail('Expected an error to be thrown');
  } catch (error) {
    expect(error).toBeInstanceOf(Error);
    // @ts-ignore
    expect(error.message).toEqual('distVersion parameter cannot be empty! Please provide the OpenSearch distribution version');
  }
});
