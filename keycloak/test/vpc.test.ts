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
  vpcStackTemplate.resourceCountIs('AWS::EC2::SecurityGroup', 3);
  vpcStackTemplate.hasResourceProperties('AWS::EC2::VPC', {
    CidrBlock: '172.31.0.0/16',
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
        CidrIp: {
          'Fn::GetAtt': [
            'KeycloakVpc50CEFB13',
            'CidrBlock',
          ],
        },
        Description: 'RDS Database access to resources within same VPC',
        FromPort: 5432,
        IpProtocol: 'tcp',
        ToPort: 5432,
      },
    ],
  });

  vpcStackTemplate.hasResourceProperties('AWS::EC2::SecurityGroupIngress', {
    Description: 'Restrict keycloak access to internal network',
    FromPort: 443,
    GroupId: {
      'Fn::GetAtt': [
        'keycloakInternalSecurityGroup77805540',
        'GroupId',
      ],
    },
    IpProtocol: 'tcp',
    SourcePrefixListId: 'pl-f8a64391',
    ToPort: 443,
  });
});
