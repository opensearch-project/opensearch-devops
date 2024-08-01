/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { Stack, StackProps } from 'aws-cdk-lib';
import {
  CertificateAuthority, CfnCertificate, CfnCertificateAuthority, CfnCertificateAuthorityActivation,
} from 'aws-cdk-lib/aws-acmpca';
import {
  Certificate, CertificateValidation, KeyAlgorithm, PrivateCertificate,
} from 'aws-cdk-lib/aws-certificatemanager';
import { HostedZone } from 'aws-cdk-lib/aws-route53';
import { Secret } from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface KeycloakUtilsProps extends StackProps {
  readonly hostedZone: string;
  readonly internalHostedZone: string;
}

export class KeycloakUtils extends Stack {
  readonly zone: HostedZone;

  readonly internalZone: HostedZone;

  readonly certificateArn: string;

  readonly internalCertificateArn: string;

  readonly keycloakDBpassword: Secret;

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

    this.internalZone = new HostedZone(this, 'internalKeycloakHostedZone', {
      zoneName: props.internalHostedZone,
    });

    const internalCertificate = new Certificate(this, 'keyCloakInternalEndpointCert', {
      domainName: props.internalHostedZone,
      validation: CertificateValidation.fromDns(this.internalZone),
    });
    this.internalCertificateArn = internalCertificate.certificateArn;

    // Generate secrets
    this.keycloakDBpassword = new Secret(this, 'keycloakDatabasePassword', {
      secretName: 'keycloak-database-password',
      description: 'RDS database password to be used with Keycloak',
    });

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

    // Generate Private certs
    const privateACMcert = new PrivateCertificate(this, 'keycloakPrivateCert', {
      domainName: props.hostedZone,
      certificateAuthority: CertificateAuthority.fromCertificateAuthorityArn(this, 'CAAuthrority', ca.attrArn),
      keyAlgorithm: KeyAlgorithm.RSA_2048,
    });

    const privateInternalACMcert = new PrivateCertificate(this, 'internalKeycloakPrivateCert', {
      domainName: props.internalHostedZone,
      certificateAuthority: CertificateAuthority.fromCertificateAuthorityArn(this, 'CAAuthrorityInternal', ca.attrArn),
      keyAlgorithm: KeyAlgorithm.RSA_2048,
    });
  }
}
