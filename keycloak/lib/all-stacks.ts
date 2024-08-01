/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { App, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { KeycloakInternalStack } from './stacks/internal-keycloak';
import { KeycloakStack } from './stacks/keycloak';
import { RdsStack } from './stacks/rds';
import { KeycloakUtils } from './stacks/utils';
import { VpcStack } from './stacks/vpc';
import { KeycloakWAF } from './waf';

export class AllStacks extends Stack {
  static readonly HOSTED_ZONE = 'keycloak.opensearch.org'

  static readonly INTERNAL_HOSTED_ZONE = 'keycloak.internal.opensearch.org'

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);
    const app = new App();

    // Create VPC
    const vpcStack = new VpcStack(app, 'keycloakVPC', {});

    // Create utilities required by different components of KeyCloak
    const utilsStack = new KeycloakUtils(app, 'KeyCloakUtils', {
      hostedZone: AllStacks.HOSTED_ZONE,
      internalHostedZone: AllStacks.INTERNAL_HOSTED_ZONE,
    });

    // Create RDS database
    const rdsDBStack = new RdsStack(app, 'KeycloakRDS', {
      vpc: vpcStack.vpc,
      rdsDbSecurityGroup: vpcStack.rdsDbSecurityGroup,
      rdsAdminPassword: utilsStack.keycloakDBpassword,
    });
    rdsDBStack.node.addDependency(vpcStack, utilsStack);

    // Deploy and install Public KeyCloak on EC2
    const keycloakStack = new KeycloakStack(app, 'Keycloak', {
      vpc: vpcStack.vpc,
      keycloakSecurityGroup: vpcStack.keyCloaksecurityGroup,
      rdsInstanceEndpoint: rdsDBStack.rdsInstanceEndpoint,
      keycloakDBpasswordSecretArn: utilsStack.keycloakDBpassword.secretFullArn,
      keycloakCertPemSecretArn: utilsStack.keycloakCertPemSecretArn,
      keycloakCertKeySecretArn: utilsStack.keycloakCertKeySecretArn,
      albProps: {
        certificateArn: utilsStack.certificateArn,
        hostedZone: utilsStack.zone,
      },
    });

    keycloakStack.node.addDependency(vpcStack, rdsDBStack, utilsStack);

    // Deploy and install Internal KeyCloak on EC2
    const keycloakInternalStack = new KeycloakInternalStack(app, 'KeycloakInternal', {
      vpc: vpcStack.vpc,
      keycloakSecurityGroup: vpcStack.keycloakInternalSecurityGroup,
      rdsInstanceEndpoint: rdsDBStack.rdsInstanceEndpoint,
      keycloakDBpasswordSecretArn: utilsStack.keycloakDBpassword.secretFullArn,
      keycloakAdminUserSecretArn: utilsStack.keycloakAdminUserSecretArn,
      keycloakAdminPasswordSecretArn: utilsStack.keycloakAdminPasswordSecretArn,
      keycloakCertPemSecretArn: utilsStack.keycloakCertPemSecretArn,
      keycloakCertKeySecretArn: utilsStack.keycloakCertKeySecretArn,
      albProps: {
        certificateArn: utilsStack.internalCertificateArn,
        hostedZone: utilsStack.internalZone,
      },
    });

    keycloakInternalStack.node.addDependency(vpcStack, rdsDBStack, utilsStack);

    // Create WAF stack
    const wafStack = new KeycloakWAF(app, 'KeycloakWAFstack', {
      loadBalancerArn: keycloakStack.loadBalancerARN,
      internalLoadBalancerArn: keycloakInternalStack.loadBalancerARN,
    });

    wafStack.node.addDependency(keycloakStack);
  }
}
