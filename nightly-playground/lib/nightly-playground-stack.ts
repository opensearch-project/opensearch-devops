/* Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0

The OpenSearch Contributors require contributions made to
this file be licensed under the Apache-2.0 license or a
compatible open source license. */

import { InfraStack } from '@opensearch-project/opensearch-cluster-cdk/lib/infra/infra-stack';
import { NetworkStack } from '@opensearch-project/opensearch-cluster-cdk/lib/networking/vpc-stack';
import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { CommonToolsStack } from './common-tools-stack';

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
    const dashboardPassword = scope.node.tryGetContext('dashboardPassword');
    if (dashboardPassword === 'undefined') {
      throw new Error('dashboardPassword parameter cannot be empty! Please provide the OpenSearch-Dashboards customized password for kibanauser');
    }

    const additionalOsdConfigString = `{"opensearch_security.auth.anonymous_auth_enabled": "true", "opensearch.password": "${dashboardPassword}", `
    + '"opensearch_security.cookie.secure": "true", "opensearch_security.cookie.isSameSite": "None"}';

    const securtityConfig = '{ "resources/security-config/config.yml" : "opensearch/config/opensearch-security/config.yml", '
    + '"resources/security-config/roles_mapping.yml" : "opensearch/config/opensearch-security/roles_mapping.yml", '
    + '"resources/security-config/roles.yml" : "opensearch/config/opensearch-security/roles.yml", '
    + '"resources/security-config/internal_users.yml": "opensearch/config/opensearch-security/internal_users.yml"}';

    const commonToolsStack = new CommonToolsStack(scope, 'commonsStack', {
      ...props,
    });
    this.stacks.push(commonToolsStack);

    // @ts-ignore
    const networkStack = new NetworkStack(scope, `networkStack-${id}`, {
      ...props,
      serverAccessType: 'ipv4',
      restrictServerAccessTo: '0.0.0.0/0',
    });

    this.stacks.push(networkStack);
    networkStack.addDependency(commonToolsStack);

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
      customConfigFiles: securtityConfig,
      additionalOsdConfig: additionalOsdConfigString,
      certificateArn: commonToolsStack.certificateArn,
      mapOpensearchPortTo: 8443,
      mapOpensearchDashboardsPortTo: 443,
    });
    this.stacks.push(infraStack);

    infraStack.addDependency(networkStack);
  }
}
