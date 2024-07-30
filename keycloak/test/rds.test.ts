/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { RdsStack } from '../lib/stacks/rds';
import { VpcStack } from '../lib/stacks/vpc';
import { KeycloakUtils } from '../lib/stacks/utils';

test('RDS Stack Test', () => {
  const app = new App();
  const vpcStack = new VpcStack(app, 'KeycloakTestVPCstack', {});
  const utilStack = new KeycloakUtils(app, 'KeycloakUtilsTestStack', {
    hostedZone: 'dummy.org',
  });
  const rdsTestStack = new RdsStack(app, 'KeycloakTestRDSstack', {
    vpc: vpcStack.vpc,
    rdsDbSecurityGroup: vpcStack.rdsDbSecurityGroup,
    rdsAdminPassword: utilStack.keycloakDBpassword,
  });
  const rdsStackTemplate = Template.fromStack(rdsTestStack);
  rdsStackTemplate.resourceCountIs('AWS::RDS::DBInstance', 1);
  rdsStackTemplate.hasResourceProperties('AWS::RDS::DBInstance', {
    AllocatedStorage: '400',
    AllowMajorVersionUpgrade: false,
    CopyTagsToSnapshot: true,
    DBInstanceClass: 'db.m5d.large',
    DBSubnetGroupName: {
      Ref: 'KeyloackDatabaseSubnetGroup225BAC34',
    },
    DeleteAutomatedBackups: false,
    DeletionProtection: true,
    Engine: 'postgres',
    EngineVersion: '15.6',
    Iops: 1000,
    Port: '5432',
    StorageEncrypted: true,
    StorageType: 'io2',
  });
});
