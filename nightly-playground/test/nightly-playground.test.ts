/* Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0

The OpenSearch Contributors require contributions made to
this file be licensed under the Apache-2.0 license or a
compatible open source license. */

import { App } from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';
import { NightlyPlaygroundStack } from '../lib/nightly-playground-stack';

test('Ensure security is always enabled with custom role mapping', () => {
  const app = new App({
    context: {
      distVersion: '2.3.0',
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
      playGroundId: '2x',
      dashboardPassword: 'foo',
      dashboardOpenIDClientSecret: 'someSecret',
    },
  });

  // WHEN
  const nightlyStack = new NightlyPlaygroundStack(app, {
    env: { account: 'test-account', region: 'us-east-1' },
  });

  // THEN
  expect(nightlyStack.stacks).toHaveLength(5);
  const infraStack = nightlyStack.stacks.filter((s) => s.stackName === 'infraStack-2x')[0];
  const infraTemplate = Template.fromStack(infraStack);

  infraTemplate.hasResourceProperties('AWS::ElasticLoadBalancingV2::Listener', {
    Port: 8443,
    Protocol: 'TCP',
  });
  infraTemplate.hasResource('AWS::AutoScaling::AutoScalingGroup', {
    /* eslint-disable max-len */
    Metadata: {
      'AWS::CloudFormation::Init': {
        config: {
          commands: {
            '010': {
              command: 'set -ex; echo "_meta:\n  type: config\n  config_version: 2\nconfig:\n  dynamic:\n    http:\n      anonymous_auth_enabled: true\n      xff:\n        enabled: false\n        internalProxies: 192\\.168\\.0\\.10|192\\.168\\.0\\.11\n    authc:\n      basic_internal_auth_domain:\n        description: Authenticate via HTTP Basic against internal users database\n        http_enabled: true\n        transport_enabled: true\n        order: 0\n        http_authenticator:\n          type: basic\n          challenge: false\n        authentication_backend:\n          type: intern\n      openid_auth_domain:\n        http_enabled: true\n        transport_enabled: true\n        order: 1\n        http_authenticator:\n          type: openid\n          challenge: false\n          config:\n            openid_connect_idp:\n              enable_ssl: true\n              verify_hostnames: false\n              pemtrustedcas_content: |\n                -----BEGIN CERTIFICATE-----\n                MIIDQTCCAimgAwIBAgITBmyfz5m/jAo54vB4ikPmljZbyjANBgkqhkiG9w0BAQsF\n                ADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6\n                b24gUm9vdCBDQSAxMB4XDTE1MDUyNjAwMDAwMFoXDTM4MDExNzAwMDAwMFowOTEL\n                MAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJv\n                b3QgQ0EgMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALJ4gHHKeNXj\n                ca9HgFB0fW7Y14h29Jlo91ghYPl0hAEvrAIthtOgQ3pOsqTQNroBvo3bSMgHFzZM\n                9O6II8c+6zf1tRn4SWiw3te5djgdYZ6k/oI2peVKVuRF4fn9tBb6dNqcmzU5L/qw\n                IFAGbHrQgLKm+a/sRxmPUDgH3KKHOVj4utWp+UhnMJbulHheb4mjUcAwhmahRWa6\n                VOujw5H5SNz/0egwLX0tdHA114gk957EWW67c4cX8jJGKLhD+rcdqsq08p8kDi1L\n                93FcXmn/6pUCyziKrlA4b9v7LWIbxcceVOF34GfID5yHI9Y/QCB/IIDEgEw+OyQm\n                jgSubJrIqg0CAwEAAaNCMEAwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMC\n                AYYwHQYDVR0OBBYEFIQYzIU07LwMlJQuCFmcx7IQTgoIMA0GCSqGSIb3DQEBCwUA\n                A4IBAQCY8jdaQZChGsV2USggNiMOruYou6r4lK5IpDB/G/wkjUu0yKGX9rbxenDI\n                U5PMCCjjmCXPI6T53iHTfIUJrU6adTrCC2qJeHZERxhlbI1Bjjt/msv0tadQ1wUs\n                N+gDS63pYaACbvXy8MWy7Vu33PqUXHeeE6V/Uq2V8viTO96LXFvKWlJbYK8U90vv\n                o/ufQJVtMVT8QtPHRh8jrdkPSHCa2XV4cdFyQzR1bldZwgJcJmApzyMZFo6IQ6XU\n                5MsI+yMRQ+hDKXJioaldXgjUkK642M4UwtBV8ob2xJNDd2ZhwLnoQdeXeGADbkpy\n                rqXRfboQnoZsG4q5WTP468SQvvG5\n                -----END CERTIFICATE-----\n            subject_key: preferred_username\n            roles_key: roles\n            openid_connect_url: >-\n              https://keycloak.opensearch.org/realms/opensearch-nightly-playgrounds/.well-known/openid-configuration\n        authentication_backend:\n          type: noop\n" > opensearch/config/opensearch-security/config.yml',
              cwd: '/home/ec2-user',
              ignoreErrors: false,
            },
            '011': {
              command: "set -ex; echo \"_meta:\n  type: rolesmapping\n  config_version: 2\nopendistro_security_anonymous_role:\n  backend_roles:\n    - opendistro_security_anonymous_backendrole\n    - default-roles-opensearch-nightly-playgrounds\nall_access:\n  reserved: false\n  backend_roles:\n    - admin\n    - admin_role_for_nightly\n  description: Maps admin to all_access\nall_access_nightly:\n  reserved: false\n  backend_roles:\n    - all_access_documentation_team\n  description: Maps all_access_documentation_team to all_access_nightly\nown_index:\n  reserved: false\n  users:\n    - '*'\n  description: Allow full access to an index named like the username\nkibana_user:\n  reserved: false\n  backend_roles:\n    - kibanauser\n  description: Maps kibanauser to kibana_user\nreadall:\n  reserved: false\n  backend_roles:\n    - readall\nkibana_server:\n  reserved: true\n  users:\n    - kibanaserver\n\" > opensearch/config/opensearch-security/roles_mapping.yml",
              cwd: '/home/ec2-user',
              ignoreErrors: false,
            },
            '012': {
              command: "set -ex; echo \"_meta:\n  type: roles\n  config_version: 2\nkibana_read_only:\n  reserved: true\nsecurity_rest_api_access:\n  reserved: true\nalerting_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/alerting/alerts/get\n    - cluster:admin/opendistro/alerting/destination/get\n    - cluster:admin/opendistro/alerting/monitor/get\n    - cluster:admin/opendistro/alerting/monitor/search\n    - cluster:admin/opensearch/alerting/findings/get\nalerting_ack_alerts:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/alerting/alerts/*\nalerting_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster_monitor\n    - cluster:admin/opendistro/alerting/*\n    - cluster:admin/opensearch/alerting/*\n    - cluster:admin/opensearch/notifications/feature/publish\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices_monitor\n        - indices:admin/aliases/get\n        - indices:admin/mappings/get\nanomaly_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/ad/detector/info\n    - cluster:admin/opendistro/ad/detector/search\n    - cluster:admin/opendistro/ad/detectors/get\n    - cluster:admin/opendistro/ad/result/search\n    - cluster:admin/opendistro/ad/tasks/search\n    - cluster:admin/opendistro/ad/detector/validate\n    - cluster:admin/opendistro/ad/result/topAnomalies\nanomaly_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster_monitor\n    - cluster:admin/opendistro/ad/*\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices_monitor\n        - indices:admin/aliases/get\n        - indices:admin/mappings/get\nknn_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/knn_search_model_action\n    - cluster:admin/knn_get_model_action\n    - cluster:admin/knn_stats_action\nknn_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/knn_training_model_action\n    - cluster:admin/knn_training_job_router_action\n    - cluster:admin/knn_training_job_route_decision_info_action\n    - cluster:admin/knn_warmup_action\n    - cluster:admin/knn_delete_model_action\n    - cluster:admin/knn_remove_model_from_cache_action\n    - cluster:admin/knn_update_model_graveyard_action\n    - cluster:admin/knn_search_model_action\n    - cluster:admin/knn_get_model_action\n    - cluster:admin/knn_stats_action\nnotebooks_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/notebooks/list\n    - cluster:admin/opendistro/notebooks/get\nnotebooks_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/notebooks/create\n    - cluster:admin/opendistro/notebooks/update\n    - cluster:admin/opendistro/notebooks/delete\n    - cluster:admin/opendistro/notebooks/get\n    - cluster:admin/opendistro/notebooks/list\nobservability_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/observability/get\nobservability_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/observability/create\n    - cluster:admin/opensearch/observability/update\n    - cluster:admin/opensearch/observability/delete\n    - cluster:admin/opensearch/observability/get\nreports_instances_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/reports/instance/list\n    - cluster:admin/opendistro/reports/instance/get\n    - cluster:admin/opendistro/reports/menu/download\nreports_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/reports/definition/get\n    - cluster:admin/opendistro/reports/definition/list\n    - cluster:admin/opendistro/reports/instance/list\n    - cluster:admin/opendistro/reports/instance/get\n    - cluster:admin/opendistro/reports/menu/download\nreports_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/reports/definition/create\n    - cluster:admin/opendistro/reports/definition/update\n    - cluster:admin/opendistro/reports/definition/on_demand\n    - cluster:admin/opendistro/reports/definition/delete\n    - cluster:admin/opendistro/reports/definition/get\n    - cluster:admin/opendistro/reports/definition/list\n    - cluster:admin/opendistro/reports/instance/list\n    - cluster:admin/opendistro/reports/instance/get\n    - cluster:admin/opendistro/reports/menu/download\nasynchronous_search_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/asynchronous_search/*\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:data/read/search*\nasynchronous_search_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/asynchronous_search/get\nindex_management_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/ism/*\n    - cluster:admin/opendistro/rollup/*\n    - cluster:admin/opendistro/transform/*\n    - cluster:admin/opensearch/notifications/feature/publish\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:admin/opensearch/ism/*\ncross_cluster_replication_leader_full_access:\n  reserved: true\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:admin/plugins/replication/index/setup/validate\n        - indices:data/read/plugins/replication/changes\n        - indices:data/read/plugins/replication/file_chunk\ncross_cluster_replication_follower_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/plugins/replication/autofollow/update\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:admin/plugins/replication/index/setup/validate\n        - indices:data/write/plugins/replication/changes\n        - indices:admin/plugins/replication/index/start\n        - indices:admin/plugins/replication/index/pause\n        - indices:admin/plugins/replication/index/resume\n        - indices:admin/plugins/replication/index/stop\n        - indices:admin/plugins/replication/index/update\n        - indices:admin/plugins/replication/index/status_check\nml_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/ml/stats/nodes\n    - cluster:admin/opensearch/ml/models/get\n    - cluster:admin/opensearch/ml/models/search\n    - cluster:admin/opensearch/ml/tasks/get\n    - cluster:admin/opensearch/ml/tasks/search\nml_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster_monitor\n    - cluster:admin/opensearch/ml/*\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices_monitor\nnotifications_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/notifications/*\nnotifications_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/notifications/configs/get\n    - cluster:admin/opensearch/notifications/features\n    - cluster:admin/opensearch/notifications/channels/get\nsnapshot_management_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/snapshot_management/*\n    - cluster:admin/opensearch/notifications/feature/publish\n    - cluster:admin/repository/*\n    - cluster:admin/snapshot/*\nsnapshot_management_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/snapshot_management/policy/get\n    - cluster:admin/opensearch/snapshot_management/policy/search\n    - cluster:admin/opensearch/snapshot_management/policy/explain\n    - cluster:admin/repository/get\n    - cluster:admin/snapshot/get\npoint_in_time_full_access:\n  reserved: true\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - manage_point_in_time\nsecurity_analytics_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/securityanalytics/alerts/get\n    - cluster:admin/opensearch/securityanalytics/detector/get\n    - cluster:admin/opensearch/securityanalytics/detector/search\n    - cluster:admin/opensearch/securityanalytics/findings/get\n    - cluster:admin/opensearch/securityanalytics/mapping/get\n    - cluster:admin/opensearch/securityanalytics/mapping/view/get\n    - cluster:admin/opensearch/securityanalytics/rule/get\n    - cluster:admin/opensearch/securityanalytics/rule/search\nsecurity_analytics_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/securityanalytics/alerts/*\n    - cluster:admin/opensearch/securityanalytics/detector/*\n    - cluster:admin/opensearch/securityanalytics/findings/*\n    - cluster:admin/opensearch/securityanalytics/mapping/*\n    - cluster:admin/opensearch/securityanalytics/rule/*\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:admin/mapping/put\n        - indices:admin/mappings/get\nsecurity_analytics_ack_alerts:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/securityanalytics/alerts/*\nopendistro_security_anonymous_role:\n  reserved: true\n  cluster_permissions:\n    - cluster:monitor/state\n    - cluster:monitor/health\n    - cluster:monitor/nodes/info\n  index_permissions:\n    - index_patterns:\n        - .kibana\n        - .kibana-6\n        - .kibana_*\n        - .opensearch_dashboards\n        - .opensearch_dashboards-6\n        - .opensearch_dashboards_*\n      allowed_actions:\n        - read\n    - index_patterns:\n        - .tasks\n        - .management-beats\n        - '*:.tasks'\n        - '*:.management-beats'\n      allowed_actions:\n        - read\n    - index_patterns:\n        - opensearch_dashboards_sample_data_logs\n        - opensearch_dashboards_sample_data_flights\n        - opensearch_dashboards_sample_data_ecommerce\n      allowed_actions:\n        - read\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - read\n        - indices:data/read/mget\n        - indices:data/read/msearch\n        - indices:data/read/mtv\n        - indices:admin/get\n        - indices:admin/aliases/exists*\n        - indices:admin/aliases/get*\n        - indices:admin/mappings/get\n        - indices:data/read/scroll\n        - indices:monitor/settings/get\n        - indices:monitor/stats\n  tenant_permissions:\n    - tenant_patterns:\n        - global_tenant\n      allowed_actions:\n        - kibana_all_read\nall_access_nightly:\n  reserved: true\n  hidden: false\n  static: true\n  description: Allow full access to all indices and all cluster APIs except security config\n  cluster_permissions:\n    - '*'\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - '*'\n  tenant_permissions:\n    - tenant_patterns:\n        - '*'\n      allowed_actions:\n        - kibana_all_write\n\" > opensearch/config/opensearch-security/roles.yml",
              cwd: '/home/ec2-user',
              ignoreErrors: false,
            },
            '017': {
              command: "set -ex;cd opensearch-dashboards/config; echo \"opensearch_security.auth.anonymous_auth_enabled: 'true'\nopensearch.password: foo\nopensearch_security.cookie.secure: 'true'\nopensearch_security.cookie.isSameSite: None\nserver.basePath: /2x\nserver.rewriteBasePath: 'true'\nopensearch.requestHeadersWhitelist:\n  - authorization\n  - securitytenant\nopensearch_security.auth.type:\n  - basicauth\n  - openid\nopensearch_security.auth.multiple_auth_enabled: 'true'\nopensearch_security.openid.connect_url: >-\n  https://keycloak.opensearch.org/realms/opensearch-nightly-playgrounds/.well-known/openid-configuration\nopensearch_security.openid.base_redirect_url: https://playground.nightly.opensearch.org/2x\nopensearch_security.openid.client_id: opensearch-dashboards-nightly-playgrounds\nopensearch_security.openid.client_secret: someSecret\nopensearch_security.ui.openid.login.buttonname: Log in with GitHub\nopensearch_security.openid.verify_hostnames: 'false'\n\">additionalOsdConfig.yml; yq eval-all -i '. as $item ireduce ({}; . * $item)' opensearch_dashboards.yml additionalOsdConfig.yml -P",
              ignoreErrors: false,
            },
          },
        },
      },
    },
  });
});

test('Throw an error for missing distVersion', () => {
  const app = new App({
    context: {
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
    },
  });
  try {
    const nightlyStack = new NightlyPlaygroundStack(app, {
      env: { account: 'test-account', region: 'us-east-1' },
    });

    // eslint-disable-next-line no-undef
    fail('Expected an error to be thrown');
  } catch (error) {
    expect(error).toBeInstanceOf(Error);
    // @ts-ignore
    expect(error.message).toEqual('distVersion parameter cannot be empty! Please provide the OpenSearch distribution version');
  }
});

test('Throw an error for missing playGroundId', () => {
  const app = new App({
    context: {
      distVersion: '3.0.0',
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
      dashboardPassword: 'bar',
    },
  });
  try {
    const nightlyStack = new NightlyPlaygroundStack(app, {
      env: { account: 'test-account', region: 'us-east-1' },
    });

    // eslint-disable-next-line no-undef
    fail('Expected an error to be thrown');
  } catch (error) {
    expect(error).toBeInstanceOf(Error);
    // @ts-ignore
    expect(error.message).toEqual('playGroundId parameter cannot be empty! Please provide one as it acts as infraStack indentifier.');
  }
});

test('Test commons stack resources', () => {
  const app = new App({
    context: {
      distVersion: '2.3.0',
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
      playGroundId: '2x',
      dashboardPassword: 'bar',
      dashboardOpenIDClientSecret: 'someSecret',
    },
  });

  // WHEN
  const nightlyStack = new NightlyPlaygroundStack(app, {
    env: { account: 'test-account', region: 'us-east-1' },
  });

  // THEN
  const commonsStack = nightlyStack.stacks.filter((s) => s.stackName === 'commonsStack')[0];
  const commonsStackTemplate = Template.fromStack(commonsStack);

  commonsStackTemplate.hasResourceProperties('AWS::Route53::HostedZone', {
    Name: 'playground.nightly.opensearch.org.',
  });
  commonsStackTemplate.resourceCountIs('AWS::S3::Bucket', 1);
  commonsStackTemplate.resourceCountIs('AWS::IAM::Role', 1);
  commonsStackTemplate.resourceCountIs('AWS::IAM::Policy', 1);
  commonsStackTemplate.hasResourceProperties('AWS::S3::Bucket', {
    BucketName: 'nightly-playgrounds-snapshots-bucket',
  });
  commonsStackTemplate.hasResourceProperties('AWS::IAM::Policy', {
    PolicyDocument: {
      Statement: [
        {
          Action: [
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
          Effect: 'Allow',
          Resource: [
            {
              'Fn::GetAtt': [
                'snapshotS3Bucket9CDAA6D3',
                'Arn',
              ],
            },
            {
              'Fn::Join': [
                '',
                [
                  {
                    'Fn::GetAtt': [
                      'snapshotS3Bucket9CDAA6D3',
                      'Arn',
                    ],
                  },
                  '/*',
                ],
              ],
            },
          ],
        },
      ],
      Version: '2012-10-17',
    },
    PolicyName: 'customInstanceRoleDefaultPolicy5AD458B6',
    Roles: [
      {
        Ref: 'customInstanceRole001450EE',
      },
    ],
  });
  commonsStackTemplate.hasResourceProperties('AWS::CertificateManager::Certificate', {
    DomainName: 'playground.nightly.opensearch.org',
    DomainValidationOptions: [
      {
        DomainName: 'playground.nightly.opensearch.org',
      },
    ],
    ValidationMethod: 'DNS',
  });
});

test('Ensure port mapping', () => {
  const app = new App({
    context: {
      distVersion: '2.3.0',
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
      playGroundId: '2x',
      dashboardPassword: 'foo',
      dashboardOpenIDClientSecret: 'someSecret',
    },
  });

  // WHEN
  const nightlyStack = new NightlyPlaygroundStack(app, {
    env: { account: 'test-account', region: 'us-east-1' },
  });

  expect(nightlyStack.stacks).toHaveLength(5);
  const infraStack = nightlyStack.stacks.filter((s) => s.stackName === 'infraStack-2x')[0];
  const infraTemplate = Template.fromStack(infraStack);

  infraTemplate.hasResourceProperties('AWS::ElasticLoadBalancingV2::Listener', {
    Port: 443,
    Protocol: 'TLS',
    Certificates: [
      {
        CertificateArn: {
          'Fn::ImportValue': Match.anyValue(),
        },
      },
    ],
  });
  infraTemplate.hasResourceProperties('AWS::ElasticLoadBalancingV2::Listener', {
    Port: 8443,
    Protocol: 'TCP',
  });
});

test('nginx load balancer and ASG resources', () => {
  const app = new App({
    context: {
      distVersion: '2.3.0',
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
      playGroundId: '2x',
      dashboardPassword: 'foo',
      endpoint2x: 'some2xNLBendpoint',
      endpoint3x: 'some3xNLBendpoint',
      dashboardOpenIDClientSecret: 'someSecret',
    },
  });

  // WHEN
  const nightlyStack = new NightlyPlaygroundStack(app, {
    env: { account: 'test-account', region: 'us-east-1' },
  });

  expect(nightlyStack.stacks).toHaveLength(5);
  const routingStack = nightlyStack.stacks.filter((s) => s.stackName === 'routingStack')[0];
  const routingStackTemplate = Template.fromStack(routingStack);

  routingStackTemplate.resourceCountIs('AWS::AutoScaling::AutoScalingGroup', 1);
  routingStackTemplate.resourceCountIs('AWS::ElasticLoadBalancingV2::LoadBalancer', 1);
  routingStackTemplate.resourceCountIs('AWS::ElasticLoadBalancingV2::Listener', 1);
  routingStackTemplate.resourceCountIs('AWS::ElasticLoadBalancingV2::TargetGroup', 1);
  routingStackTemplate.hasResourceProperties('AWS::ElasticLoadBalancingV2::Listener', {
    Port: 443,
    Protocol: 'HTTPS',
    Certificates: [
      {
        CertificateArn: {
          'Fn::ImportValue': Match.anyValue(),
        },
      },
    ],
  });
  routingStackTemplate.hasResource('AWS::AutoScaling::AutoScalingGroup', {
    /* eslint-disable max-len */
    Metadata: {
      'AWS::CloudFormation::Init': {
        config: {
          files: {
            '/etc/nginx/conf.d/opensearchdashboard.conf': {
              content: 'resolver 10.0.0.2 ipv6=off;\n              \n              server {\n                  listen 443;\n                  server_name playground.nightly.opensearch.org;\n              \n                  ssl_certificate /etc/nginx/cert.crt;\n                  ssl_certificate_key /etc/nginx/cert.key;\n              \n                  ssl on;\n                  ssl_session_cache builtin:1000 shared:SSL:10m;\n                  ssl_protocols TLSv1 TLSv1.1 TLSv1.2;\n                  ssl_ciphers HIGH:!aNULL:!eNULL:!EXPORT:!CAMELLIA:!DES:!MD5:!PSK:!RC4;\n                  ssl_prefer_server_ciphers on;\n              \n                  location ^~ /2x {\n                      proxy_pass https://some2xNLBendpoint/2x;\n                      proxy_set_header X-Real-IP $remote_addr;  # Set the X-Real-IP header\n                      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # Set the X-Forwarded-For header\n                      proxy_set_header X-Forwarded-Proto $scheme;  # Set the X-Forwarded-Proto header\n                      proxy_buffer_size   128k;\n                      proxy_buffers   4 256k;\n                      proxy_busy_buffers_size   256k;\n                  }\n                  location ^~ /3x {\n                    proxy_pass https://some3xNLBendpoint/3x;\n                    proxy_set_header X-Real-IP $remote_addr;  # Set the X-Real-IP header\n                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # Set the X-Forwarded-For header\n                    proxy_set_header X-Forwarded-Proto $scheme;  # Set the X-Forwarded-Proto header\n                    proxy_buffer_size   128k;\n                    proxy_buffers   4 256k;\n                    proxy_busy_buffers_size   256k;\n                }\n              }',
              encoding: 'plain',
              mode: '000644',
              owner: 'root',
              group: 'root',
            },
          },
          commands: {
            '000': {
              command: 'amazon-linux-extras install nginx1.12 -y',
            },
            '001': {
              command: "openssl req -x509 -nodes -newkey rsa:4096 -keyout /etc/nginx/cert.key -out /etc/nginx/cert.crt -days 365 -subj '/CN=SH'",
            },
            '002': {
              command: 'cp /usr/share/nginx/html/index_nightly.html /usr/share/nginx/html/index.html',
            },
            '003': {
              command: 'sudo systemctl start nginx',
            },
            '004': {
              command: 'sudo systemctl enable nginx',
            },
          },
        },
      },
    },
  });
});

test('WAF resources', () => {
  const app = new App({
    context: {
      distVersion: '2.3.0',
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
      playGroundId: '2x',
      dashboardPassword: 'foo',
      endpoint2x: 'some2xNLBendpoint',
      endpoint3x: 'some3xNLBendpoint',
      dashboardOpenIDClientSecret: 'someSecret',
    },
  });

  // WHEN
  const nightlyStack = new NightlyPlaygroundStack(app, {
    env: { account: 'test-account', region: 'us-east-1' },
  });

  expect(nightlyStack.stacks).toHaveLength(5);
  const wafStack = nightlyStack.stacks.filter((s) => s.stackName === 'wafStack')[0];
  const wafStackTemplate = Template.fromStack(wafStack);

  wafStackTemplate.resourceCountIs('AWS::WAFv2::WebACL', 1);
  wafStackTemplate.resourceCountIs('AWS::WAFv2::WebACLAssociation', 1);
  wafStackTemplate.hasResourceProperties('AWS::WAFv2::WebACL', {
    DefaultAction: {
      Allow: {},
    },
    Scope: 'REGIONAL',
    VisibilityConfig: {
      CloudWatchMetricsEnabled: true,
      MetricName: 'nightly-playground-WAF',
      SampledRequestsEnabled: true,
    },
    Name: 'nightly-playground-WAF',
    Rules: [
      {
        Name: 'AWS-AWSManagedRulesAmazonIpReputationList',
        OverrideAction: {
          None: {},
        },
        Priority: 0,
        Statement: {
          ManagedRuleGroupStatement: {
            Name: 'AWSManagedRulesAmazonIpReputationList',
            VendorName: 'AWS',
          },
        },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'AWSManagedRulesAmazonIpReputationList',
          SampledRequestsEnabled: true,
        },
      },
      {
        Name: 'AWS-AWSManagedRulesSQLiRuleSet',
        OverrideAction: {
          None: {},
        },
        Priority: 1,
        Statement: {
          ManagedRuleGroupStatement: {
            ExcludedRules: [],
            Name: 'AWSManagedRulesSQLiRuleSet',
            VendorName: 'AWS',
          },
        },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'AWS-AWSManagedRulesSQLiRuleSet',
          SampledRequestsEnabled: true,
        },
      },
      {
        Name: 'AWS-AWSManagedRulesWordPressRuleSet',
        OverrideAction: {
          None: {},
        },
        Priority: 2,
        Statement: {
          ManagedRuleGroupStatement: {
            ExcludedRules: [],
            Name: 'AWSManagedRulesWordPressRuleSet',
            VendorName: 'AWS',
          },
        },
        VisibilityConfig: {
          CloudWatchMetricsEnabled: true,
          MetricName: 'AWS-AWSManagedRulesWordPressRuleSet',
          SampledRequestsEnabled: true,
        },
      },
    ],
  });
});
