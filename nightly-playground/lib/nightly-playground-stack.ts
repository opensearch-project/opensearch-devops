/* Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0

The OpenSearch Contributors require contributions made to
this file be licensed under the Apache-2.0 license or a
compatible open source license. */

import { InfraStack } from '@opensearch-project/opensearch-cluster-cdk/lib/infra/infra-stack';
import { NetworkStack } from '@opensearch-project/opensearch-cluster-cdk/lib/networking/vpc-stack';
import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class NightlyPlaygroundStack {
  public stacks: Stack[] = []; // only required for testing purpose

  constructor(scope: Construct, id: string, props: StackProps) {
    const distVersion = scope.node.tryGetContext('distVersion');
    if (distVersion === 'undefined') {
      throw new Error('distVersion parameter cannot be empty! Please provide the OpenSearch distribution version');
    }
    const distributionUrl = scope.node.tryGetContext('distributionUrl');
    if (distributionUrl === 'undefined') {
      throw new Error('distributionUrl parameter cannot be empty! Please provide the OpenSearch distribution URL');
    }
    const dashboardsUrl = scope.node.tryGetContext('dashboardsUrl');
    if (dashboardsUrl === 'undefined') {
      throw new Error('dashboardsUrl parameter cannot be empty! Please provide the OpenSearch-Dashboards distribution URL');
    }

    // @ts-ignore
    const networkStack = new NetworkStack(scope, `networkStack-${id}`, {
      ...props,
      serverAccessType: 'prefixList',
      restrictServerAccessTo: 'pl-f8a64391',
    });

    this.stacks.push(networkStack);

    // @ts-ignore
    const infraStack = new InfraStack(scope, `infraStack-${id}`, {
      ...props,
      vpc: networkStack.vpc,
      securityGroup: networkStack.osSecurityGroup,
      cpuArch: 'x64',
      opensearchVersion: distVersion,
      minDistribution: false,
      securityDisabled: false,
      enableMonitoring: true,
      distributionUrl,
      singleNodeCluster: false,
      dashboardsUrl,
    });
    this.stacks.push(infraStack);

    infraStack.addDependency(networkStack);
  }
}
