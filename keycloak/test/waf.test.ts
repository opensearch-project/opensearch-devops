/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { KeycloakWAF } from '../lib/waf';

test('VPC Stack Test', () => {
  const app = new App();
  const wafStack = new KeycloakWAF(app, 'keycloakWAFtest', {
    loadBalancerArn: 'loadbalancer:arn',
    internalLoadBalancerArn: 'internal:loadBalancer:arn',
  });

  const wafStackTemplate = Template.fromStack(wafStack);

  wafStackTemplate.resourceCountIs('AWS::WAFv2::WebACL', 1);
  wafStackTemplate.resourceCountIs('AWS::WAFv2::WebACLAssociation', 2);
  wafStackTemplate.hasResourceProperties('AWS::WAFv2::WebACL', {
    DefaultAction: {
      Allow: {},
    },
    Name: 'Keycloak-WAF',
    Rules: [
      {
        Name: 'AWS-AWSManagedRulesAmazonIpReputationList',
        OverrideAction: {
          None: {},
        },
        Priority: 0,
        Statement: {
          ManagedRuleGroupStatement: {
            Name: 'AWSManagedRulesAmazonIpReputationList',
            VendorName: 'AWS',
          },
        },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'AWSManagedRulesAmazonIpReputationList',
          SampledRequestsEnabled: true,
        },
      },
      {
        Name: 'AWS-AWSManagedRulesSQLiRuleSet',
        OverrideAction: {
          None: {},
        },
        Priority: 1,
        Statement: {
          ManagedRuleGroupStatement: {
            ExcludedRules: [],
            Name: 'AWSManagedRulesSQLiRuleSet',
            VendorName: 'AWS',
          },
        },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'AWS-AWSManagedRulesSQLiRuleSet',
          SampledRequestsEnabled: true,
        },
      },
      {
        Name: 'AWS-AWSManagedRulesWordPressRuleSet',
        OverrideAction: {
          None: {},
        },
        Priority: 2,
        Statement: {
          ManagedRuleGroupStatement: {
            ExcludedRules: [],
            Name: 'AWSManagedRulesWordPressRuleSet',
            VendorName: 'AWS',
          },
        },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'AWS-AWSManagedRulesWordPressRuleSet',
          SampledRequestsEnabled: true,
        },
      },
    ],
    Scope: 'REGIONAL',
    VisibilityConfig: {
      CloudWatchMetricsEnabled: true,
      MetricName: 'Keycloak-WAF',
      SampledRequestsEnabled: true,
    },
  });
});
