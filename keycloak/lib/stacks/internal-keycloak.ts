/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { Duration, Stack } from 'aws-cdk-lib';
import {
  AutoScalingGroup, BlockDeviceVolume, Monitoring, Signals,
} from 'aws-cdk-lib/aws-autoscaling';
import {
  AmazonLinuxCpuType, CloudFormationInit, InitCommand, InitElement, InitFile, InitPackage,
  InstanceClass, InstanceSize, InstanceType, MachineImage,
  SubnetType,
} from 'aws-cdk-lib/aws-ec2';
import {
  ApplicationLoadBalancer, ApplicationProtocol, ListenerCertificate, Protocol, SslPolicy,
} from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import {
  ManagedPolicy, PolicyStatement, Role, ServicePrincipal,
} from 'aws-cdk-lib/aws-iam';
import { ARecord, RecordTarget } from 'aws-cdk-lib/aws-route53';
import { LoadBalancerTarget } from 'aws-cdk-lib/aws-route53-targets';
import { Construct } from 'constructs';
import { join } from 'path';
import { KeyCloakProps } from './keycloak';

export class KeycloakInternalStack extends Stack {
  readonly loadBalancerARN: string

  constructor(scope: Construct, id: string, props: KeyCloakProps) {
    super(scope, id, props);

    const instanceRole = this.createInstanceRole();

    const keycloakNodeAsg = new AutoScalingGroup(this, 'keycloakInternalASG', {
      instanceType: InstanceType.of(InstanceClass.C5, InstanceSize.XLARGE9),
      machineImage: MachineImage.latestAmazonLinux2023({
        cpuType: AmazonLinuxCpuType.X86_64,
      }),
      role: instanceRole,
      initOptions: {
        ignoreFailures: true,
      },
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: SubnetType.PRIVATE_WITH_EGRESS,
      },
      minCapacity: 1,
      maxCapacity: 1,
      desiredCapacity: 1,
      init: CloudFormationInit.fromElements(...KeycloakInternalStack.getCfnInitConfig(this.region, props)),
      blockDevices: [{
        deviceName: '/dev/xvda',
        volume: BlockDeviceVolume.ebs(100, {}),
      }],
      signals: Signals.waitForAll({
        timeout: Duration.minutes(20),
      }),
      requireImdsv2: true,
      instanceMonitoring: Monitoring.DETAILED,
    });

    const alb = new ApplicationLoadBalancer(this, 'keycloakInternalALB', {
      vpc: props.vpc,
      internetFacing: true,
      securityGroup: props.keycloakSecurityGroup,
    });
    this.loadBalancerARN = alb.loadBalancerArn;

    const listenerCertificate = ListenerCertificate.fromArn(props.albProps.certificateArn);

    const listener = alb.addListener('keycloakInternalListener', {
      port: 443,
      protocol: ApplicationProtocol.HTTPS,
      sslPolicy: SslPolicy.RECOMMENDED_TLS,
      certificates: [listenerCertificate],
    });

    listener.addTargets('keycloakInternalALBTarget', {
      port: 8443,
      protocol: ApplicationProtocol.HTTPS,
      healthCheck: {
        port: '8443',
        path: '/',
        protocol: Protocol.HTTPS,
      },
      targets: [keycloakNodeAsg],
    });

    const aRecord = new ARecord(this, 'keyCloakALBinternalRecord', {
      zone: props.albProps.hostedZone,
      recordName: props.albProps.hostedZone.zoneName,
      target: RecordTarget.fromAlias(new LoadBalancerTarget(alb)),
    });
  }

  private static getCfnInitConfig(region: string, props: KeyCloakProps): InitElement[] {
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

  private createInstanceRole(): Role {
    const role = new Role(this, 'internal-keycloak-instance-role', {
      assumedBy: new ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
        ManagedPolicy.fromAwsManagedPolicyName('SecretsManagerReadWrite'),
      ],
    });
    role.addManagedPolicy(new ManagedPolicy(this, 'cloudwatchPolicy', {
      description: 'Cloudwatch Agent Permissions',
      statements: [new PolicyStatement({
        actions: [
          'logs:CreateLogStream',
          'logs:CreateLogDelivery',
          'logs:DeleteLogDelivery',
          'logs:CreateLogGroup',
        ],
        resources: ['*'],
        conditions: {
          'ForAllValues:StringEquals': {
            'aws:RequestedRegion': this.region,
            'aws:PrincipalAccount': this.account,
          },
        },
      })],
    }));
    return role;
  }
}
