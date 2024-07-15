/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import { AutoScalingGroup, BlockDeviceVolume, Monitoring, Signals } from 'aws-cdk-lib/aws-autoscaling';
import { AmazonLinuxCpuType, CloudFormationInit, InitCommand, InitElement, InitFile, InitPackage, InstanceClass, InstanceSize, InstanceType, MachineImage, Peer, Port, SecurityGroup, SubnetType, Vpc } from 'aws-cdk-lib/aws-ec2';
import { ApplicationLoadBalancer, ApplicationProtocol, ListenerCertificate, Protocol, SslPolicy } from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import { ManagedPolicy, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { ARecord, RecordTarget } from 'aws-cdk-lib/aws-route53';
import { Construct } from 'constructs';
import { join } from 'path';
import { KeycloakUtils } from './utils';
import { LoadBalancerTarget } from 'aws-cdk-lib/aws-route53-targets';

export interface ALBprops {
  certificateArn: string;
  hostedZone: KeycloakUtils;
}
export interface KeyCloakProps extends StackProps {
  vpc: Vpc;
  keycloakSecurityGroup: SecurityGroup;
  rdsInstanceEndpoint: string;
  keycloakDBpasswordSecretArn: string;
  keycloakAdminUserSecretArn: string;
  keycloakAdminPasswordSecretArn: string;
  keycloakCertPemSecretArn: string;
  keycloakCertKeySecretArn: string;
  albProps: ALBprops
}

export class KeycloakStack extends Stack {
  constructor(scope: Construct, id: string, props: KeyCloakProps) {
    super(scope, id, props)

    const instanceRole = this.createInstanceRole();

    const keycloakNodeAsg = new AutoScalingGroup(this, 'keycloakASG', {
      instanceType: InstanceType.of(InstanceClass.C5, InstanceSize.XLARGE9),
      machineImage: MachineImage.latestAmazonLinux2023({
        cpuType: AmazonLinuxCpuType.X86_64,
      }),
      role: instanceRole,
      initOptions: {
        ignoreFailures: false,
      },
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: SubnetType.PRIVATE_WITH_EGRESS,
      },
      minCapacity: 1,
      maxCapacity: 1,
      desiredCapacity: 1,
      init: CloudFormationInit.fromElements(...KeycloakStack.getCfnInitConfig(this.region, props)),
      blockDevices: [{
        deviceName: '/dev/xvda',
        volume: BlockDeviceVolume.ebs(100, {})
      }],
      signals: Signals.waitForAll({
        timeout: Duration.minutes(20),
      }),
      requireImdsv2: true,
      instanceMonitoring: Monitoring.DETAILED,
    });

    const alb = new ApplicationLoadBalancer(this, 'keycloakALB', {
      vpc: props.vpc,
      internetFacing: true,
      securityGroup: props.keycloakSecurityGroup
    })

    const listenerCertificate = ListenerCertificate.fromArn(props.albProps.certificateArn);

    const listener = alb.addListener('keycloakListener', {
      port: 443,
      protocol: ApplicationProtocol.HTTPS,
      sslPolicy: SslPolicy.RECOMMENDED_TLS,
      certificates: [listenerCertificate]
    });

    listener.addTargets('keycloakALBTarget', {
      port: 443,
      protocol: ApplicationProtocol.HTTPS,
      healthCheck: {
        port: '80',
        path: '/',
        protocol: Protocol.HTTP
      },
      targets: [keycloakNodeAsg]
    });

    const aRecord = new ARecord(this, 'keyCloakALB-record', {
      zone: props.albProps.hostedZone.zone,
      recordName: props.albProps.hostedZone.zone.zoneName,
      target: RecordTarget.fromAlias(new LoadBalancerTarget(alb)),
    });

  }

  private static getCfnInitConfig(region: string, props: KeyCloakProps): InitElement[] {
    return [
      InitPackage.yum('docker'),
      InitCommand.shellCommand('sudo curl -L https://github.com/docker/compose/releases/download/v2.9.0/docker-compose-$(uname -s)-$(uname -m) -o /usr/bin/docker-compose && sudo chmod +x /usr/bin/docker-compose'),
      InitFile.fromFileInline('/docker-compose.yml', join(__dirname, '../../resources/docker-compose.yml')),
      InitCommand.shellCommand('touch /.env'),
      InitCommand.shellCommand(`echo KC_DB_PASSWORD=$(aws --region ${region} secretsmanager get-secret-value --secret-id ${props.keycloakDBpasswordSecretArn} --query SecretString --output text) > /.env && `
        + `echo KEYCLOAK_ADMIN_LOGIN=$(aws --region ${region} secretsmanager get-secret-value --secret-id ${props.keycloakAdminUserSecretArn} --query SecretString --output text) >> /.env && `
        + `echo KEYCLOAK_ADMIN_PASSWORD=$(aws --region ${region} secretsmanager get-secret-value --secret-id ${props.keycloakAdminPasswordSecretArn} --query SecretString --output text) >> /.env && `
        + `echo RDS_HOSTNAME_WITH_PORT=${props.rdsInstanceEndpoint} >> /.env`),
      InitCommand.shellCommand(`mkdir /certs && aws --region ${region} secretsmanager get-secret-value --secret-id ${props.keycloakCertPemSecretArn} --query SecretString --output text > /certs/keycloak.pem && aws --region ${region} secretsmanager get-secret-value --secret-id ${props.keycloakCertKeySecretArn} --query SecretString --output text > /certs/keycloak.key`),
      InitCommand.shellCommand('systemctl start docker && docker-compose up -d'),
    ]
  }

  private createInstanceRole(): Role {
    const role = new Role(this, 'keycloak-instance-role', {
      assumedBy: new ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
        ManagedPolicy.fromAwsManagedPolicyName('SecretsManagerReadWrite')
      ]
    });
    return role;
  }
}
