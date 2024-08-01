/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { AllStacks } from '../lib/all-stacks';
import { KeycloakUtils } from '../lib/stacks/utils';

test('Utils Stack Test', () => {
  const app = new App();
  const utilsStack = new KeycloakUtils(app, 'KeycloakTestUtilsStack', {
    hostedZone: AllStacks.HOSTED_ZONE,
    internalHostedZone: AllStacks.INTERNAL_HOSTED_ZONE,
  });
  const utilsStackTemplate = Template.fromStack(utilsStack);
  utilsStackTemplate.resourceCountIs('AWS::Route53::HostedZone', 2);
  utilsStackTemplate.resourceCountIs('AWS::CertificateManager::Certificate', 4);
  utilsStackTemplate.resourceCountIs('AWS::SecretsManager::Secret', 5);
  utilsStackTemplate.resourceCountIs('AWS::ACMPCA::CertificateAuthority', 1);
  utilsStackTemplate.resourceCountIs('AWS::ACMPCA::Certificate', 1);
  utilsStackTemplate.resourceCountIs('AWS::ACMPCA::CertificateAuthorityActivation', 1);
  utilsStackTemplate.hasResourceProperties('AWS::Route53::HostedZone', {
    Name: 'keycloak.opensearch.org.',
  });
  utilsStackTemplate.hasResourceProperties('AWS::ACMPCA::CertificateAuthority', {
    KeyAlgorithm: 'RSA_2048',
    SigningAlgorithm: 'SHA256WITHRSA',
    Subject: {
      Country: 'US',
      Locality: 'Seattle',
      Organization: 'OpenSearch',
      OrganizationalUnit: 'Engineering Effectiveness',
      State: 'Washington',
    },
    Type: 'ROOT',
  });
  utilsStackTemplate.hasResourceProperties('AWS::ACMPCA::Certificate', {
    CertificateAuthorityArn: {
      'Fn::GetAtt': [
        'CA',
        'Arn',
      ],
    },
    CertificateSigningRequest: {
      'Fn::GetAtt': [
        'CA',
        'CertificateSigningRequest',
      ],
    },
    SigningAlgorithm: 'SHA256WITHRSA',
    TemplateArn: 'arn:aws:acm-pca:::template/RootCACertificate/V1',
    Validity: {
      Type: 'YEARS',
      Value: 10,
    },
  });
});
