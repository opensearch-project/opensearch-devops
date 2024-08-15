/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import {
  RemovalPolicy,
  Stack, StackProps,
} from 'aws-cdk-lib';
import {
  InstanceClass, InstanceSize, InstanceType, SecurityGroup, Vpc,
} from 'aws-cdk-lib/aws-ec2';
import {
  DatabaseInstance, DatabaseInstanceEngine, PostgresEngineVersion, StorageType,
} from 'aws-cdk-lib/aws-rds';
import { Secret } from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface RdsStackProps extends StackProps {
  readonly vpc: Vpc;
  readonly rdsDbSecurityGroup: SecurityGroup;
  readonly rdsAdminPassword: Secret
}
export class RdsStack extends Stack {
  readonly rdsInstanceEndpoint: string;

  constructor(scope: Construct, id: string, props: RdsStackProps) {
    super(scope, id);
    const keycloakDatabase = new DatabaseInstance(this, 'KeyloackDatabase', {
      engine: DatabaseInstanceEngine.postgres({ version: PostgresEngineVersion.VER_15_6 }),
      vpc: props.vpc,
      allocatedStorage: 400,
      storageType: StorageType.IO2,
      storageEncrypted: true,
      instanceType: InstanceType.of(InstanceClass.M5D, InstanceSize.LARGE),
      removalPolicy: RemovalPolicy.RETAIN,
      allowMajorVersionUpgrade: false,
      deleteAutomatedBackups: false,
      port: 5432,
      securityGroups: [props.rdsDbSecurityGroup],
      credentials: {
        username: 'keycloak',
        password: props.rdsAdminPassword.secretValue,
      },
    });
    this.rdsInstanceEndpoint = keycloakDatabase.instanceEndpoint.socketAddress;
  }
}
