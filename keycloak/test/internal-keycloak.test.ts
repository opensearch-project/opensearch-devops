/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { App } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';
import { InitCommand } from 'aws-cdk-lib/aws-ec2';
import { KeycloakStack } from '../lib/stacks/keycloak';
import { RdsStack } from '../lib/stacks/rds';
import { KeycloakUtils } from '../lib/stacks/utils';
import { VpcStack } from '../lib/stacks/vpc';

test('Internal Keycloak Installation Test', () => {
  const app = new App();
  const vpcStack = new VpcStack(app, 'KeycloakTestVPCstack', {});
  const keycloakUtilsStack = new KeycloakUtils(app, 'KeycloakUtilsTestStack', {
    hostedZone: 'keycloak.opensearch.org',
    internalHostedZone: 'keycloak.internal.opensearch.org',
  });
  const rdsStack = new RdsStack(app, 'RDSTestStack', {
    vpc: vpcStack.vpc,
    rdsDbSecurityGroup: vpcStack.rdsDbSecurityGroup,
    rdsAdminPassword: keycloakUtilsStack.keycloakDbPassword,
  });
  const keycloakInternalStack = new KeycloakStack(app, 'KeycloakInternalTestStack', {
    vpc: vpcStack.vpc,
    keycloakSecurityGroup: vpcStack.keyCloaksecurityGroup,
    certificateArn: 'some:arn',
    hostedZone: keycloakUtilsStack.zone,
    initConfig: [InitCommand.shellCommand('something')],
  });
  const keycloakStackTemplate = Template.fromStack(keycloakInternalStack);
  keycloakStackTemplate.resourceCountIs('AWS::IAM::Role', 1);
  keycloakStackTemplate.resourceCountIs('AWS::AutoScaling::AutoScalingGroup', 1);
  keycloakStackTemplate.resourceCountIs('AWS::ElasticLoadBalancingV2::LoadBalancer', 1);
  keycloakStackTemplate.resourceCountIs('AWS::ElasticLoadBalancingV2::Listener', 1);
  keycloakStackTemplate.hasResourceProperties('AWS::ElasticLoadBalancingV2::Listener', {
    DefaultActions: [
      {
        TargetGroupArn: {
          Ref: Match.anyValue(),
        },
        Type: 'forward',
      },
    ],
    LoadBalancerArn: {
      Ref: Match.anyValue(),
    },
    Port: 443,
    Protocol: 'HTTPS',
    SslPolicy: 'ELBSecurityPolicy-TLS13-1-2-2021-06',
  });
});
