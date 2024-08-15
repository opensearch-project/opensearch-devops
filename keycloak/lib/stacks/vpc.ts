/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { Stack, StackProps } from 'aws-cdk-lib';
import {
  IpAddresses, Peer, Port, SecurityGroup,
  Vpc,
} from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export class VpcStack extends Stack {
  public readonly vpc: Vpc;

  public readonly keyCloaksecurityGroup: SecurityGroup

  public readonly rdsDbSecurityGroup: SecurityGroup

  public readonly keycloakInternalSecurityGroup: SecurityGroup

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id);
    this.vpc = new Vpc(this, 'KeycloakVpc', {
      ipAddresses: IpAddresses.cidr('172.31.0.0/16'),
      maxAzs: 3,
    });
    this.keyCloaksecurityGroup = new SecurityGroup(this, 'keycloakSecurityGroup', {
      vpc: this.vpc,
    });
    this.keyCloaksecurityGroup.addIngressRule(Peer.anyIpv4(), Port.tcp(443), 'Allow inbound HTTPS traffic');
    this.keyCloaksecurityGroup.addIngressRule(this.keyCloaksecurityGroup, Port.tcp(8443), 'Allow access to keycloak');

    this.keycloakInternalSecurityGroup = new SecurityGroup(this, 'keycloakInternalSecurityGroup', {
      vpc: this.vpc,
    });
    this.keycloakInternalSecurityGroup.addIngressRule(Peer.prefixList('pl-f8a64391'), Port.tcp(443), 'Restrict keycloak access to internal network');
    this.keycloakInternalSecurityGroup.addIngressRule(this.keycloakInternalSecurityGroup, Port.tcp(8443), 'Allow access to keycloak');

    this.rdsDbSecurityGroup = new SecurityGroup(this, 'rdsSecurityGroup', {
      vpc: this.vpc,
    });

    this.rdsDbSecurityGroup.addIngressRule(Peer.ipv4(this.vpc.vpcCidrBlock), Port.tcp(5432),
      'RDS Database access to resources within same VPC');
  }
}
