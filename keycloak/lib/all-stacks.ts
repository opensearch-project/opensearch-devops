/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { App, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { VpcStack } from './stacks/vpc';
import { KeycloakUtils } from './stacks/utils';
import { RdsStack } from './stacks/rds';
import { KeycloakStack } from './stacks/keycloak';
import { KeycloakWAF } from './waf';

export class AllStacks extends Stack {
  static readonly HOSTED_ZONE = 'keycloak.opensearch.org'

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);
    const app = new App();

    // Create VPC
    const vpcStack = new VpcStack(app, 'keycloakVPC', {});

    // Create utilities required by different components of KeyCloak
    const utilsStack = new KeycloakUtils(app, 'KeyCloakUtils', {
      hostedZone: AllStacks.HOSTED_ZONE,
    });

    // Create RDS database
    const rdsDBStack = new RdsStack(app, 'KeycloakRDS', {
      vpc: vpcStack.vpc,
      rdsDbSecurityGroup: vpcStack.rdsDbSecurityGroup,
      rdsAdminPassword: utilsStack.keycloakDBpassword,
    });
    rdsDBStack.node.addDependency(vpcStack, utilsStack);

    // Deploy and install KeyCloak on EC2
    const keycloakStack = new KeycloakStack(app, 'Keycloak', {
      vpc: vpcStack.vpc,
      keycloakSecurityGroup: vpcStack.keyCloaksecurityGroup,
      rdsInstanceEndpoint: rdsDBStack.rdsInstanceEndpoint,
      keycloakDBpasswordSecretArn: utilsStack.keycloakDBpassword.secretFullArn,
      keycloakAdminUserSecretArn: utilsStack.keycloakAdminUserSecretArn,
      keycloakAdminPasswordSecretArn: utilsStack.keycloakAdminPasswordSecretArn,
      keycloakCertPemSecretArn: utilsStack.keycloakCertPemSecretArn,
      keycloakCertKeySecretArn: utilsStack.keycloakCertKeySecretArn,
      albProps: {
        certificateArn: utilsStack.certificateArn,
        hostedZone: utilsStack,
      },
    });

    keycloakStack.node.addDependency(vpcStack, rdsDBStack, utilsStack);

    // Create WAF stack
    const wafStack = new KeycloakWAF(app, 'KeycloakWAFstack', {
      loadBalancerArn: keycloakStack.loadBalancerARN,
    });

    wafStack.node.addDependency(keycloakStack);
  }
}
