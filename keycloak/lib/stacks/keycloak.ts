/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import {
  AutoScalingGroup, BlockDeviceVolume, Monitoring, Signals,
} from 'aws-cdk-lib/aws-autoscaling';
import {
  AmazonLinuxCpuType, CloudFormationInit,
  InitCommand,
  InitElement,
  InitFile,
  InitPackage,
  InstanceClass, InstanceSize, InstanceType, MachineImage,
  SecurityGroup, SubnetType, Vpc,
} from 'aws-cdk-lib/aws-ec2';
import {
  ApplicationLoadBalancer, ApplicationProtocol, ListenerCertificate, Protocol, SslPolicy,
} from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import {
  ManagedPolicy, PolicyStatement, Role, ServicePrincipal,
} from 'aws-cdk-lib/aws-iam';
import { ARecord, HostedZone, RecordTarget } from 'aws-cdk-lib/aws-route53';
import { LoadBalancerTarget } from 'aws-cdk-lib/aws-route53-targets';
import { Construct } from 'constructs';
import { join } from 'path';
import { KeycloakMonitoring } from './monitoring';

export interface InitProps {
  rdsInstanceEndpoint: string;
  keycloakCertPemSecretArn: string;
  keycloakCertKeySecretArn: string;
  keycloakDBpasswordSecretArn?: string;
  keycloakAdminUserSecretArn?: string;
  keycloakAdminPasswordSecretArn?: string;
}

export interface KeyCloakProps extends StackProps {
  vpc: Vpc;
  initConfig: InitElement[];
  keycloakSecurityGroup: SecurityGroup;
  certificateArn: string;
  hostedZone: HostedZone;
}

export class KeycloakStack extends Stack {
  readonly loadBalancerArn: string

  constructor(scope: Construct, id: string, props: KeyCloakProps) {
    super(scope, id, props);

    const instanceRole = this.createInstanceRole(id);

    const keycloakNodeAsg = new AutoScalingGroup(this, `${id}-keycloakASG`, {
      instanceType: InstanceType.of(InstanceClass.C5, InstanceSize.XLARGE2),
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
      init: CloudFormationInit.fromElements(...props.initConfig),
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

    const keycloakAlb = new ApplicationLoadBalancer(this, `${id}-keycloakALB`, {
      vpc: props.vpc,
      internetFacing: true,
      securityGroup: props.keycloakSecurityGroup,
    });
    this.loadBalancerArn = keycloakAlb.loadBalancerArn;

    const listenerCertificate = ListenerCertificate.fromArn(props.certificateArn);

    const listener = keycloakAlb.addListener(`${id}-keycloakListener`, {
      port: 443,
      protocol: ApplicationProtocol.HTTPS,
      sslPolicy: SslPolicy.RECOMMENDED_TLS,
      certificates: [listenerCertificate],
    });

    const keycloakTargetGroup = listener.addTargets(`${id}-keycloakALBTarget`, {
      port: 8443,
      protocol: ApplicationProtocol.HTTPS,
      healthCheck: {
        port: '8443',
        path: '/health',
        protocol: Protocol.HTTPS,
      },
      targets: [keycloakNodeAsg],
    });

    const aRecord = new ARecord(this, `${id}-keyCloakALB-record`, {
      zone: props.hostedZone,
      recordName: props.hostedZone.zoneName,
      target: RecordTarget.fromAlias(new LoadBalancerTarget(keycloakAlb)),
    });

    // Add monitoring
    new KeycloakMonitoring(this, `${id}-monitoring`, {
      targetGroup: keycloakTargetGroup,
      autoScalingGroup: keycloakNodeAsg,
    });
  }

  private createInstanceRole(id: string): Role {
    const role = new Role(this, `${id}-keycloak-instance-role`, {
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

  public static getCfnInitConfigForPublicKeycloak(region: string, props: InitProps): InitElement[] {
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

  public static getCfnInitConfigForInternalKeycloak(region: string, props: InitProps): InitElement[] {
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
