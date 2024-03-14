/* Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0

The OpenSearch Contributors require contributions made to
this file be licensed under the Apache-2.0 license or a
compatible open source license. */

import { Stack, StackProps } from 'aws-cdk-lib';
import { Certificate, CertificateValidation } from 'aws-cdk-lib/aws-certificatemanager';
import { HostedZone } from 'aws-cdk-lib/aws-route53';
import { Construct } from 'constructs';

export class CommonToolsStack extends Stack {
    readonly certificateArn: string

    constructor(scope: Construct, id: string, props: StackProps) {
      super(scope, id, props);
      const zone = 'playground.nightly.opensearch.org';

      const route53HostedZone = new HostedZone(this, 'nigghhtlyHostedZone', {
        zoneName: zone,
      });

      const certificate = new Certificate(this, 'cert', {
        domainName: zone,
        validation: CertificateValidation.fromDns(route53HostedZone),
      });
      this.certificateArn = certificate.certificateArn;
    }
}
