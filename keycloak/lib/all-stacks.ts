/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { Stack, StackProps } from 'aws-cdk-lib';
import {
  InitCommand, InitElement, InitFile, InitPackage,
} from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';
import { join } from 'path';
import { InitProps, KeycloakStack } from './stacks/keycloak';
import { RdsStack } from './stacks/rds';
import { KeycloakUtils } from './stacks/utils';
import { VpcStack } from './stacks/vpc';
import { KeycloakWAF } from './waf';

export class AllStacks extends Stack {
  static readonly HOSTED_ZONE = 'keycloak.opensearch.org'

  static readonly INTERNAL_HOSTED_ZONE = 'keycloak.internal.opensearch.org'

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // Create VPC
    const vpcStack = new VpcStack(this, 'keycloakVPC', {});

    // Create utilities required by different components of KeyCloak
    const utilsStack = new KeycloakUtils(this, 'KeyCloakUtils', {
      hostedZone: AllStacks.HOSTED_ZONE,
      internalHostedZone: AllStacks.INTERNAL_HOSTED_ZONE,
    });

    // Create RDS database
    const rdsDBStack = new RdsStack(this, 'KeycloakRDS', {
      vpc: vpcStack.vpc,
      rdsDbSecurityGroup: vpcStack.rdsDbSecurityGroup,
      rdsAdminPassword: utilsStack.keycloakDbPassword,
    });
    rdsDBStack.node.addDependency(vpcStack, utilsStack);

    // Deploy and install Public KeyCloak on EC2
    const keycloakStack = new KeycloakStack(this, 'public', {
      vpc: vpcStack.vpc,
      keycloakSecurityGroup: vpcStack.keyCloaksecurityGroup,
      certificateArn: utilsStack.certificateArn,
      hostedZone: utilsStack.zone,
      initConfig: AllStacks.getCfnInitConfigForPublicKeycloak(this.region, {
        rdsInstanceEndpoint: rdsDBStack.rdsInstanceEndpoint,
        keycloakDBpasswordSecretArn: utilsStack.keycloakDbPassword.secretFullArn,
        keycloakCertPemSecretArn: utilsStack.keycloakCertPemSecretArn,
        keycloakCertKeySecretArn: utilsStack.keycloakCertKeySecretArn,
      }),
    });

    keycloakStack.node.addDependency(vpcStack, rdsDBStack, utilsStack);

    // Deploy and install Internal KeyCloak on EC2
    const keycloakInternalStack = new KeycloakStack(this, 'internal', {
      vpc: vpcStack.vpc,
      keycloakSecurityGroup: vpcStack.keycloakInternalSecurityGroup,
      certificateArn: utilsStack.internalCertificateArn,
      hostedZone: utilsStack.internalZone,
      initConfig: AllStacks.getCfnInitConfigForInternalKeycloak(this.region, {
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
    const wafStack = new KeycloakWAF(this, 'KeycloakWAFstack', {
      loadBalancerArn: keycloakStack.loadBalancerArn,
      internalLoadBalancerArn: keycloakInternalStack.loadBalancerArn,
    });

    wafStack.node.addDependency(keycloakStack);
  }

  private static getCfnInitConfigForPublicKeycloak(region: string, props: InitProps): InitElement[] {
    return [
      InitPackage.yum('docker'),
      InitCommand.shellCommand('sudo curl -L https://github.com/docker/compose/releases/download/v2.9.0/docker-compose-$(uname -s)-$(uname -m) '
        + '-o /usr/bin/docker-compose && sudo chmod +x /usr/bin/docker-compose'),
      InitFile.fromFileInline('/docker-compose.yml', join(__dirname, '../../resources/docker-compose.yml')),
      InitCommand.shellCommand('touch /.env'),
      InitCommand.shellCommand(`echo KC_DB_PASSWORD=$(aws --region ${region} secretsmanager get-secret-value`
        + ` --secret-id ${props.keycloakDBpasswordSecretArn} --query SecretString --output text) > /.env && `
        + `echo RDS_HOSTNAME_WITH_PORT=${props.rdsInstanceEndpoint} >> /.env`),
      InitCommand.shellCommand(`mkdir /certs && aws --region ${region} secretsmanager get-secret-value --secret-id`
        + ` ${props.keycloakCertPemSecretArn} --query SecretString --output text > /certs/keycloak.pem && aws --region ${region}`
        + ` secretsmanager get-secret-value --secret-id ${props.keycloakCertKeySecretArn} --query SecretString --output text > /certs/keycloak.key`),
      InitCommand.shellCommand('systemctl start docker && docker-compose up -d'),
    ];
  }

  private static getCfnInitConfigForInternalKeycloak(region: string, props: InitProps): InitElement[] {
    return [
      InitPackage.yum('docker'),
      InitCommand.shellCommand('sudo curl -L https://github.com/docker/compose/releases/download/v2.9.0/docker-compose-$(uname -s)-$(uname -m) '
        + '-o /usr/bin/docker-compose && sudo chmod +x /usr/bin/docker-compose'),
      InitFile.fromFileInline('/docker-compose.yml', join(__dirname, '../../resources/internal-docker-compose.yml')),
      InitCommand.shellCommand('touch /.env'),
      InitCommand.shellCommand(`echo KC_DB_PASSWORD=$(aws --region ${region} secretsmanager get-secret-value`
        + ` --secret-id ${props.keycloakDBpasswordSecretArn} --query SecretString --output text) > /.env && `
        + `echo KEYCLOAK_ADMIN_LOGIN=$(aws --region ${region} secretsmanager get-secret-value --secret-id ${props.keycloakAdminUserSecretArn}`
        + ' --query SecretString --output text) >> /.env && '
        + `echo KEYCLOAK_ADMIN_PASSWORD=$(aws --region ${region} secretsmanager get-secret-value`
        + ` --secret-id ${props.keycloakAdminPasswordSecretArn} --query SecretString --output text) >> /.env && `
        + `echo RDS_HOSTNAME_WITH_PORT=${props.rdsInstanceEndpoint} >> /.env`),
      InitCommand.shellCommand(`mkdir /certs && aws --region ${region} secretsmanager get-secret-value --secret-id`
        + ` ${props.keycloakCertPemSecretArn} --query SecretString --output text > /certs/keycloak.pem && aws --region ${region}`
        + ` secretsmanager get-secret-value --secret-id ${props.keycloakCertKeySecretArn} --query SecretString --output text > /certs/keycloak.key`),
      InitCommand.shellCommand('systemctl start docker && docker-compose up -d'),
    ];
  }
}
