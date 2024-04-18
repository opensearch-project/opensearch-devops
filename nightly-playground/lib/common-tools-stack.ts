/* Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0

The OpenSearch Contributors require contributions made to
this file be licensed under the Apache-2.0 license or a
compatible open source license. */

import { Stack, StackProps } from 'aws-cdk-lib';
import { Certificate, CertificateValidation } from 'aws-cdk-lib/aws-certificatemanager';
import {
  Effect, ManagedPolicy, PolicyStatement, Role, ServicePrincipal,
} from 'aws-cdk-lib/aws-iam';
import { HostedZone } from 'aws-cdk-lib/aws-route53';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export class CommonToolsStack extends Stack {
  readonly certificateArn: string

  public readonly customRole: Role

  readonly zone = 'playground.nightly.opensearch.org'

  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    const route53HostedZone = new HostedZone(this, 'nigghhtlyHostedZone', {
      zoneName: this.zone,
    });

    const certificate = new Certificate(this, 'cert', {
      domainName: this.zone,
      validation: CertificateValidation.fromDns(route53HostedZone),
    });
    this.certificateArn = certificate.certificateArn;

    this.customRole = new Role(this, 'customInstanceRole', {
      managedPolicies: [ManagedPolicy.fromAwsManagedPolicyName('AmazonEC2ReadOnlyAccess'),
        ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore')],
      assumedBy: new ServicePrincipal('ec2.amazonaws.com'),
    });

    const snapshotS3Bucket = new Bucket(this, 'snapshotS3Bucket', {
      bucketName: 'nightly-playgrounds-snapshots-bucket',
    });

    const s3bucketPolicyStatement = new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:ListBucket',
        's3:GetBucketLocation',
        's3:ListBucketMultipartUploads',
        's3:ListBucketVersions',
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:AbortMultipartUpload',
        's3:ListMultipartUploadParts',
      ],
      resources: [snapshotS3Bucket.bucketArn, `${snapshotS3Bucket.bucketArn}/*`],
    });

    this.customRole.addToPolicy(s3bucketPolicyStatement);
  }
}
