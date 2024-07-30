/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { VpcStack } from '../lib/stacks/vpc';

test('VPC Stack Test', () => {
  const app = new App();
  const vpcStack = new VpcStack(app, 'keycloakTestStack', {});
  const vpcStackTemplate = Template.fromStack(vpcStack);
  vpcStackTemplate.resourceCountIs('AWS::EC2::VPC', 1);
  vpcStackTemplate.resourceCountIs('AWS::EC2::Subnet', 4);
  vpcStackTemplate.resourceCountIs('AWS::EC2::SecurityGroup', 2);
  vpcStackTemplate.hasResourceProperties('AWS::EC2::VPC', {
    CidrBlock: '172.31.0.0/16',
  });
  vpcStackTemplate.hasResourceProperties('AWS::EC2::SecurityGroupIngress', {
    Description: 'Allow access to keycloak',
    FromPort: 8443,
    GroupId: {
      'Fn::GetAtt': [
        'keycloakSecurityGroupF4E0E54E',
        'GroupId',
      ],
    },
    IpProtocol: 'tcp',
    SourceSecurityGroupId: {
      'Fn::GetAtt': [
        'keycloakSecurityGroupF4E0E54E',
        'GroupId',
      ],
    },
    ToPort: 8443,
  });
  vpcStackTemplate.hasResourceProperties('AWS::EC2::SecurityGroup', {
    SecurityGroupIngress: [
      {
        CidrIp: '0.0.0.0/0',
        Description: 'Allow inbound HTTPS traffic',
        FromPort: 443,
        IpProtocol: 'tcp',
        ToPort: 443,
      },
    ],
  });
  vpcStackTemplate.hasResourceProperties('AWS::EC2::SecurityGroup', {
    SecurityGroupIngress: [
      {
        Description: 'RDS Database access',
        FromPort: 5432,
        IpProtocol: 'tcp',
        SourceSecurityGroupId: {
          'Fn::GetAtt': [
            'keycloakSecurityGroupF4E0E54E',
            'GroupId',
          ],
        },
        ToPort: 5432,
      },
    ],
  });
});
