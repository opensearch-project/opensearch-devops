/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { Stack, StackProps } from 'aws-cdk-lib';
import { CfnCertificate, CfnCertificateAuthority, CfnCertificateAuthorityActivation } from 'aws-cdk-lib/aws-acmpca';
import { Certificate, CertificateValidation } from 'aws-cdk-lib/aws-certificatemanager';
import { HostedZone } from 'aws-cdk-lib/aws-route53';
import { Secret } from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface KeycloakUtilsProps extends StackProps {
  readonly hostedZone: string,
}

export class KeycloakUtils extends Stack {
  readonly zone: HostedZone;

  readonly certificateArn: string;

  readonly keycloakDBpasswordSecretArn: string;

  readonly keycloakAdminUserSecretArn: string;

  readonly keycloakAdminPasswordSecretArn: string;

  readonly keycloakCertPemSecretArn: string;

  readonly keycloakCertKeySecretArn: string;

  constructor(scope: Construct, id: string, props: KeycloakUtilsProps) {
    super(scope, id, props);
    // Generate Domain Name and Domain Cert
    this.zone = new HostedZone(this, 'keycloakHostedZone', {
      zoneName: props.hostedZone,
    });

    const certificate = new Certificate(this, 'keyCloakEndpointCert', {
      domainName: props.hostedZone,
      validation: CertificateValidation.fromDns(this.zone),
    });
    this.certificateArn = certificate.certificateArn;

    // Generate secrets
    const keycloakDBpassword = new Secret(this, 'keycloakDatabasePassword', {
      secretName: 'keycloak-database-password',
      description: 'RDS database password to be used with Keycloak',
    });
    this.keycloakDBpasswordSecretArn = keycloakDBpassword.secretArn;

    const keycloakAdminUser = new Secret(this, 'keycloakAdminUser', {
      secretName: 'keycloak-admin-user',
      description: 'Keycloak admin username',
    });
    this.keycloakAdminUserSecretArn = keycloakAdminUser.secretArn;

    const keycloakAdminPassword = new Secret(this, 'keycloakAdminPassword', {
      secretName: 'keycloak-admin-password',
      description: 'Keycloak admin password',
    });
    this.keycloakAdminPasswordSecretArn = keycloakAdminPassword.secretArn;

    const keycloakCertPem = new Secret(this, 'keycloakCertPem', {
      secretName: 'keycloak-cert-pem',
      description: 'Keycloak Certificate PEM file',
    });
    this.keycloakCertPemSecretArn = keycloakCertPem.secretArn;

    const keycloakCertKey = new Secret(this, 'keycloakCertKey', {
      secretName: 'keycloak-cert-key',
      description: 'Keycloak Certificate Key file',
    });
    this.keycloakCertKeySecretArn = keycloakCertKey.secretArn;

    // Generate a ROOT CA
    const ca = new CfnCertificateAuthority(this, 'CA', {
      type: 'ROOT',
      keyAlgorithm: 'RSA_2048',
      signingAlgorithm: 'SHA256WITHRSA',
      subject: {
        country: 'US',
        organization: 'OpenSearch',
        organizationalUnit: 'Engineering Effectiveness',
        state: 'Washington',
        locality: 'Seattle',
      },
    });

    const caSignedCertificate = new CfnCertificate(this, 'CertificateCreation', {
      certificateAuthorityArn: ca.attrArn,
      signingAlgorithm: 'SHA256WITHRSA',
      certificateSigningRequest: ca.attrCertificateSigningRequest,
      templateArn: 'arn:aws:acm-pca:::template/RootCACertificate/V1',
      validity: {
        type: 'YEARS',
        value: 10,
      },
    });

    new CfnCertificateAuthorityActivation(this, 'CAActivation', {
      certificate: caSignedCertificate.attrCertificate,
      certificateAuthorityArn: ca.attrArn,
      status: 'ACTIVE',
    });
  }
}
