/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import {
  IpAddresses, Peer, Port, SecurityGroup, SelectedSubnets, SubnetType, Vpc,
} from 'aws-cdk-lib/aws-ec2';
import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class VpcStack extends Stack {
  public readonly vpc: Vpc;

  public readonly keyCloaksecurityGroup: SecurityGroup

  public readonly rdsDbSecurityGroup: SecurityGroup

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id);
    this.vpc = new Vpc(this, 'KeycloakVpc', {
      ipAddresses: IpAddresses.cidr('172.31.0.0/16'),

    });
    this.keyCloaksecurityGroup = new SecurityGroup(this, 'keycloakSecurityGroup', {
      vpc: this.vpc,
    });
    this.keyCloaksecurityGroup.addIngressRule(Peer.anyIpv4(), Port.tcp(443), 'Allow inbound HTTPS traffic');
    this.keyCloaksecurityGroup.addIngressRule(this.keyCloaksecurityGroup, Port.tcp(8443), 'Allow access to keycloak');

    this.rdsDbSecurityGroup = new SecurityGroup(this, 'rdsSecurityGroup', {
      vpc: this.vpc,
    });
    this.rdsDbSecurityGroup.addIngressRule(Peer.securityGroupId(this.keyCloaksecurityGroup.securityGroupId), Port.tcp(5432), 'RDS Database access');
  }
}
