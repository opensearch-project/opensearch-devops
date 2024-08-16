/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { App } from 'aws-cdk-lib';
import 'source-map-support/register';
import { KeycloakStack } from '../lib/stacks/keycloak';
import { RdsStack } from '../lib/stacks/rds';
import { KeycloakUtils } from '../lib/stacks/utils';
import { VpcStack } from '../lib/stacks/vpc';
import { KeycloakWAF } from '../lib/waf';

const app = new App();

const region = app.node.tryGetContext('region') ?? process.env.CDK_DEFAULT_REGION;
const account = app.node.tryGetContext('account') ?? process.env.CDK_DEFAULT_ACCOUNT;
const HOSTED_ZONE = 'keycloak.opensearch.org';
const INTERNAL_HOSTED_ZONE = 'keycloak.internal.opensearch.org';

// Create VPC
const vpcStack = new VpcStack(app, 'keycloakVPC', {});

// Create utilities required by different components of KeyCloak
const utilsStack = new KeycloakUtils(app, 'KeyCloakUtils', {
  env: { account, region },
  hostedZone: HOSTED_ZONE,
  internalHostedZone: INTERNAL_HOSTED_ZONE,
});

// Create RDS database
const rdsDBStack = new RdsStack(app, 'KeycloakRDS', {
  env: { account, region },
  vpc: vpcStack.vpc,
  rdsDbSecurityGroup: vpcStack.rdsDbSecurityGroup,
  rdsAdminPassword: utilsStack.keycloakDbPassword,
});
rdsDBStack.node.addDependency(vpcStack, utilsStack);

// Deploy and install Public KeyCloak on EC2
const keycloakStack = new KeycloakStack(app, 'PublicKeycloak', {
  env: { account, region },
  vpc: vpcStack.vpc,
  keycloakSecurityGroup: vpcStack.keyCloaksecurityGroup,
  certificateArn: utilsStack.certificateArn,
  hostedZone: utilsStack.zone,
  initConfig: KeycloakStack.getCfnInitConfigForPublicKeycloak(region, {
    rdsInstanceEndpoint: rdsDBStack.rdsInstanceEndpoint,
    keycloakDBpasswordSecretArn: utilsStack.keycloakDbPassword.secretFullArn,
    keycloakCertPemSecretArn: utilsStack.keycloakCertPemSecretArn,
    keycloakCertKeySecretArn: utilsStack.keycloakCertKeySecretArn,
  }),
});

keycloakStack.node.addDependency(vpcStack, rdsDBStack, utilsStack);

// Deploy and install Internal KeyCloak on EC2
const keycloakInternalStack = new KeycloakStack(app, 'InternalKeycloak', {
  env: { account, region },
  vpc: vpcStack.vpc,
  keycloakSecurityGroup: vpcStack.keycloakInternalSecurityGroup,
  certificateArn: utilsStack.internalCertificateArn,
  hostedZone: utilsStack.internalZone,
  initConfig: KeycloakStack.getCfnInitConfigForInternalKeycloak(region, {
    rdsInstanceEndpoint: rdsDBStack.rdsInstanceEndpoint,
    keycloakDBpasswordSecretArn: utilsStack.keycloakDbPassword.secretFullArn,
    keycloakAdminUserSecretArn: utilsStack.keycloakAdminUserSecretArn,
    keycloakAdminPasswordSecretArn: utilsStack.keycloakAdminPasswordSecretArn,
    keycloakCertPemSecretArn: utilsStack.keycloakCertPemSecretArn,
    keycloakCertKeySecretArn: utilsStack.keycloakCertKeySecretArn,
  }),
});

keycloakInternalStack.node.addDependency(vpcStack, rdsDBStack, utilsStack);

// Create WAF stack
const wafStack = new KeycloakWAF(app, 'KeycloakWAFstack', {
  env: { account, region },
  loadBalancerArn: keycloakStack.loadBalancerArn,
  internalLoadBalancerArn: keycloakInternalStack.loadBalancerArn,
});

wafStack.node.addDependency(keycloakStack);
