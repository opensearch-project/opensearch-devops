/* Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0

The OpenSearch Contributors require contributions made to
this file be licensed under the Apache-2.0 license or a
compatible open source license. */

import { Stack, StackProps } from 'aws-cdk-lib';
import { AutoScalingGroup, Signals } from 'aws-cdk-lib/aws-autoscaling';
import {
  AmazonLinuxCpuType, AmazonLinuxGeneration,
  CloudFormationInit, ISecurityGroup,
  IVpc, InitCommand,
  InitElement, InitFile,
  InstanceClass, InstanceSize,
  InstanceType, MachineImage, SubnetType,
} from 'aws-cdk-lib/aws-ec2';
import {
  ApplicationLoadBalancer, ApplicationProtocol, ListenerCertificate,
  SslPolicy,
} from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import { Construct } from 'constructs';
import { join } from 'path';

export interface RoutingProps extends StackProps {
    readonly vpc: IVpc;
    readonly securityGroup: ISecurityGroup
    readonly certificateArn: string
    readonly endpoint2x : string
    readonly endpoint3x: string
    readonly domainName: string
}

export class Routing extends Stack {
  readonly alb: ApplicationLoadBalancer

  constructor(scope: Construct, id: string, props: RoutingProps) {
    super(scope, id, props);

    this.alb = new ApplicationLoadBalancer(this, 'alb', {
      vpc: props.vpc,
      internetFacing: true,
      securityGroup: props.securityGroup,
    });

    const listener = this.alb.addListener('NginxProxyAlbListener', {
      port: 443,
      protocol: ApplicationProtocol.HTTPS,
      sslPolicy: SslPolicy.RECOMMENDED_TLS,
      certificates: [ListenerCertificate.fromArn(props.certificateArn)],
    });

    const ngnix = new AutoScalingGroup(this, 'ngnixBasedRouting', {
      vpc: props.vpc,
      instanceType: InstanceType.of(InstanceClass.M5, InstanceSize.LARGE),
      machineImage: MachineImage.latestAmazonLinux({
        generation: AmazonLinuxGeneration.AMAZON_LINUX_2,
        cpuType: AmazonLinuxCpuType.X86_64,
      }),
      maxCapacity: 1,
      minCapacity: 1,
      desiredCapacity: 1,
      vpcSubnets: {
        subnetType: SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroup: props.securityGroup,
      init: CloudFormationInit.fromElements(...Routing.getCfnInitElement(props)),
      initOptions: {
        ignoreFailures: true,
      },
      requireImdsv2: true,
      signals: Signals.waitForAll(),
    });

    listener.addTargets('ngnixTargetGroup', {
      port: 443,
      protocol: ApplicationProtocol.HTTPS,
      healthCheck: {
        port: '443',
        path: '/',
      },
      targets: [ngnix],
    });
  }

  private static getCfnInitElement(ngnixProps: RoutingProps): InitElement[] {
    const cfnInitConfig: InitElement[] = [
      InitCommand.shellCommand('amazon-linux-extras install nginx1.12 -y'),
      InitCommand.shellCommand('openssl req -x509 -nodes -newkey rsa:4096 -keyout /etc/nginx/cert.key -out /etc/nginx/cert.crt -days 365 -subj \'/CN=SH\''),
      InitFile.fromString('/etc/nginx/conf.d/opensearchdashboard.conf',
        `resolver 10.0.0.2 ipv6=off;
              
              server {
                  listen 443;
                  server_name ${ngnixProps.domainName};
              
                  ssl_certificate /etc/nginx/cert.crt;
                  ssl_certificate_key /etc/nginx/cert.key;
              
                  ssl on;
                  ssl_session_cache builtin:1000 shared:SSL:10m;
                  ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
                  ssl_ciphers HIGH:!aNULL:!eNULL:!EXPORT:!CAMELLIA:!DES:!MD5:!PSK:!RC4;
                  ssl_prefer_server_ciphers on;
              
                  location ^~ /2x {
                      proxy_pass https://${ngnixProps.endpoint2x}/2x;
                      proxy_set_header X-Real-IP $remote_addr;  # Set the X-Real-IP header
                      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # Set the X-Forwarded-For header
                      proxy_set_header X-Forwarded-Proto $scheme;  # Set the X-Forwarded-Proto header
                  }
                  location ^~ /3x {
                    proxy_pass https://${ngnixProps.endpoint3x}/3x;
                    proxy_set_header X-Real-IP $remote_addr;  # Set the X-Real-IP header
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # Set the X-Forwarded-For header
                    proxy_set_header X-Forwarded-Proto $scheme;  # Set the X-Forwarded-Proto header
                }
              }`),
      InitFile.fromFileInline('/usr/share/nginx/html/index_nightly.html', join(__dirname, '../resources/assets/ngnix-index.html')),
      InitCommand.shellCommand('cp /usr/share/nginx/html/index_nightly.html /usr/share/nginx/html/index.html'),
      InitCommand.shellCommand('sudo systemctl start nginx'),
      InitCommand.shellCommand('sudo systemctl enable nginx'),
    ];
    return cfnInitConfig;
  }
}
