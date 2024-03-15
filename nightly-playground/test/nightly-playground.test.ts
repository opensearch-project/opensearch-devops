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
    },
  });

  // WHEN
  const nightlyStack = new NightlyPlaygroundStack(app, '2x', {
    env: { account: 'test-account', region: 'us-east-1' },
  });

  // THEN
  expect(nightlyStack.stacks).toHaveLength(3);
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
              command: 'set -ex; echo "_meta:\n  type: config\n  config_version: 2\nconfig:\n  dynamic:\n    http:\n      anonymous_auth_enabled: true\n      xff:\n        enabled: false\n        internalProxies: 192\\.168\\.0\\.10|192\\.168\\.0\\.11\n    authc:\n      kerberos_auth_domain:\n        http_enabled: false\n        transport_enabled: false\n        order: 6\n        http_authenticator:\n          type: kerberos\n          challenge: true\n          config:\n            krb_debug: false\n            strip_realm_from_principal: true\n        authentication_backend:\n          type: noop\n      basic_internal_auth_domain:\n        description: Authenticate via HTTP Basic against internal users database\n        http_enabled: true\n        transport_enabled: true\n        order: 4\n        http_authenticator:\n          type: basic\n          challenge: true\n        authentication_backend:\n          type: intern\n      proxy_auth_domain:\n        description: Authenticate via proxy\n        http_enabled: false\n        transport_enabled: false\n        order: 3\n        http_authenticator:\n          type: proxy\n          challenge: false\n          config:\n            user_header: x-proxy-user\n            roles_header: x-proxy-roles\n        authentication_backend:\n          type: noop\n      jwt_auth_domain:\n        description: Authenticate via Json Web Token\n        http_enabled: false\n        transport_enabled: false\n        order: 0\n        http_authenticator:\n          type: jwt\n          challenge: false\n          config:\n            signing_key: base64 encoded HMAC key or public RSA/ECDSA pem key\n            jwt_header: Authorization\n            jwt_url_parameter: null\n            jwt_clock_skew_tolerance_seconds: 30\n            roles_key: null\n            subject_key: null\n        authentication_backend:\n          type: noop\n      clientcert_auth_domain:\n        description: Authenticate via SSL client certificates\n        http_enabled: false\n        transport_enabled: false\n        order: 2\n        http_authenticator:\n          type: clientcert\n          config:\n            username_attribute: cn\n          challenge: false\n        authentication_backend:\n          type: noop\n      ldap:\n        description: Authenticate via LDAP or Active Directory\n        http_enabled: false\n        transport_enabled: false\n        order: 5\n        http_authenticator:\n          type: basic\n          challenge: false\n        authentication_backend:\n          type: ldap\n          config:\n            enable_ssl: false\n            enable_start_tls: false\n            enable_ssl_client_auth: false\n            verify_hostnames: true\n            hosts:\n              - localhost:8389\n            bind_dn: null\n            password: null\n            userbase: ou=people,dc=example,dc=com\n            usersearch: (sAMAccountName={0})\n            username_attribute: null\n    authz:\n      roles_from_myldap:\n        description: Authorize via LDAP or Active Directory\n        http_enabled: false\n        transport_enabled: false\n        authorization_backend:\n          type: ldap\n          config:\n            enable_ssl: false\n            enable_start_tls: false\n            enable_ssl_client_auth: false\n            verify_hostnames: true\n            hosts:\n              - localhost:8389\n            bind_dn: null\n            password: null\n            rolebase: ou=groups,dc=example,dc=com\n            rolesearch: (member={0})\n            userroleattribute: null\n            userrolename: disabled\n            rolename: cn\n            resolve_nested_roles: true\n            userbase: ou=people,dc=example,dc=com\n            usersearch: (uid={0})\n      roles_from_another_ldap:\n        description: Authorize via another Active Directory\n        http_enabled: false\n        transport_enabled: false\n        authorization_backend:\n          type: ldap\n" > opensearch/config/opensearch-security/config.yml',
              cwd: '/home/ec2-user',
              ignoreErrors: false,
            },
            '011': {
              command: "set -ex; echo \"_meta:\n  type: rolesmapping\n  config_version: 2\nopendistro_security_anonymous_role:\n  backend_roles:\n    - opendistro_security_anonymous_backendrole\nall_access:\n  reserved: false\n  backend_roles:\n    - admin\n  description: Maps admin to all_access\nown_index:\n  reserved: false\n  users:\n    - '*'\n  description: Allow full access to an index named like the username\nkibana_user:\n  reserved: false\n  backend_roles:\n    - kibanauser\n  description: Maps kibanauser to kibana_user\nreadall:\n  reserved: false\n  backend_roles:\n    - readall\nkibana_server:\n  reserved: true\n  users:\n    - kibanaserver\n\" > opensearch/config/opensearch-security/roles_mapping.yml",
              cwd: '/home/ec2-user',
              ignoreErrors: false,
            },
            '012': {
              command: "set -ex; echo \"_meta:\n  type: roles\n  config_version: 2\nkibana_read_only:\n  reserved: true\nsecurity_rest_api_access:\n  reserved: true\nalerting_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/alerting/alerts/get\n    - cluster:admin/opendistro/alerting/destination/get\n    - cluster:admin/opendistro/alerting/monitor/get\n    - cluster:admin/opendistro/alerting/monitor/search\n    - cluster:admin/opensearch/alerting/findings/get\nalerting_ack_alerts:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/alerting/alerts/*\nalerting_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster_monitor\n    - cluster:admin/opendistro/alerting/*\n    - cluster:admin/opensearch/alerting/*\n    - cluster:admin/opensearch/notifications/feature/publish\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices_monitor\n        - indices:admin/aliases/get\n        - indices:admin/mappings/get\nanomaly_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/ad/detector/info\n    - cluster:admin/opendistro/ad/detector/search\n    - cluster:admin/opendistro/ad/detectors/get\n    - cluster:admin/opendistro/ad/result/search\n    - cluster:admin/opendistro/ad/tasks/search\n    - cluster:admin/opendistro/ad/detector/validate\n    - cluster:admin/opendistro/ad/result/topAnomalies\nanomaly_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster_monitor\n    - cluster:admin/opendistro/ad/*\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices_monitor\n        - indices:admin/aliases/get\n        - indices:admin/mappings/get\nknn_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/knn_search_model_action\n    - cluster:admin/knn_get_model_action\n    - cluster:admin/knn_stats_action\nknn_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/knn_training_model_action\n    - cluster:admin/knn_training_job_router_action\n    - cluster:admin/knn_training_job_route_decision_info_action\n    - cluster:admin/knn_warmup_action\n    - cluster:admin/knn_delete_model_action\n    - cluster:admin/knn_remove_model_from_cache_action\n    - cluster:admin/knn_update_model_graveyard_action\n    - cluster:admin/knn_search_model_action\n    - cluster:admin/knn_get_model_action\n    - cluster:admin/knn_stats_action\nnotebooks_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/notebooks/list\n    - cluster:admin/opendistro/notebooks/get\nnotebooks_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/notebooks/create\n    - cluster:admin/opendistro/notebooks/update\n    - cluster:admin/opendistro/notebooks/delete\n    - cluster:admin/opendistro/notebooks/get\n    - cluster:admin/opendistro/notebooks/list\nobservability_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/observability/get\nobservability_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/observability/create\n    - cluster:admin/opensearch/observability/update\n    - cluster:admin/opensearch/observability/delete\n    - cluster:admin/opensearch/observability/get\nreports_instances_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/reports/instance/list\n    - cluster:admin/opendistro/reports/instance/get\n    - cluster:admin/opendistro/reports/menu/download\nreports_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/reports/definition/get\n    - cluster:admin/opendistro/reports/definition/list\n    - cluster:admin/opendistro/reports/instance/list\n    - cluster:admin/opendistro/reports/instance/get\n    - cluster:admin/opendistro/reports/menu/download\nreports_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/reports/definition/create\n    - cluster:admin/opendistro/reports/definition/update\n    - cluster:admin/opendistro/reports/definition/on_demand\n    - cluster:admin/opendistro/reports/definition/delete\n    - cluster:admin/opendistro/reports/definition/get\n    - cluster:admin/opendistro/reports/definition/list\n    - cluster:admin/opendistro/reports/instance/list\n    - cluster:admin/opendistro/reports/instance/get\n    - cluster:admin/opendistro/reports/menu/download\nasynchronous_search_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/asynchronous_search/*\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:data/read/search*\nasynchronous_search_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/asynchronous_search/get\nindex_management_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opendistro/ism/*\n    - cluster:admin/opendistro/rollup/*\n    - cluster:admin/opendistro/transform/*\n    - cluster:admin/opensearch/notifications/feature/publish\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:admin/opensearch/ism/*\ncross_cluster_replication_leader_full_access:\n  reserved: true\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:admin/plugins/replication/index/setup/validate\n        - indices:data/read/plugins/replication/changes\n        - indices:data/read/plugins/replication/file_chunk\ncross_cluster_replication_follower_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/plugins/replication/autofollow/update\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:admin/plugins/replication/index/setup/validate\n        - indices:data/write/plugins/replication/changes\n        - indices:admin/plugins/replication/index/start\n        - indices:admin/plugins/replication/index/pause\n        - indices:admin/plugins/replication/index/resume\n        - indices:admin/plugins/replication/index/stop\n        - indices:admin/plugins/replication/index/update\n        - indices:admin/plugins/replication/index/status_check\nml_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/ml/stats/nodes\n    - cluster:admin/opensearch/ml/models/get\n    - cluster:admin/opensearch/ml/models/search\n    - cluster:admin/opensearch/ml/tasks/get\n    - cluster:admin/opensearch/ml/tasks/search\nml_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster_monitor\n    - cluster:admin/opensearch/ml/*\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices_monitor\nnotifications_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/notifications/*\nnotifications_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/notifications/configs/get\n    - cluster:admin/opensearch/notifications/features\n    - cluster:admin/opensearch/notifications/channels/get\nsnapshot_management_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/snapshot_management/*\n    - cluster:admin/opensearch/notifications/feature/publish\n    - cluster:admin/repository/*\n    - cluster:admin/snapshot/*\nsnapshot_management_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/snapshot_management/policy/get\n    - cluster:admin/opensearch/snapshot_management/policy/search\n    - cluster:admin/opensearch/snapshot_management/policy/explain\n    - cluster:admin/repository/get\n    - cluster:admin/snapshot/get\npoint_in_time_full_access:\n  reserved: true\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - manage_point_in_time\nsecurity_analytics_read_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/securityanalytics/alerts/get\n    - cluster:admin/opensearch/securityanalytics/detector/get\n    - cluster:admin/opensearch/securityanalytics/detector/search\n    - cluster:admin/opensearch/securityanalytics/findings/get\n    - cluster:admin/opensearch/securityanalytics/mapping/get\n    - cluster:admin/opensearch/securityanalytics/mapping/view/get\n    - cluster:admin/opensearch/securityanalytics/rule/get\n    - cluster:admin/opensearch/securityanalytics/rule/search\nsecurity_analytics_full_access:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/securityanalytics/alerts/*\n    - cluster:admin/opensearch/securityanalytics/detector/*\n    - cluster:admin/opensearch/securityanalytics/findings/*\n    - cluster:admin/opensearch/securityanalytics/mapping/*\n    - cluster:admin/opensearch/securityanalytics/rule/*\n  index_permissions:\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - indices:admin/mapping/put\n        - indices:admin/mappings/get\nsecurity_analytics_ack_alerts:\n  reserved: true\n  cluster_permissions:\n    - cluster:admin/opensearch/securityanalytics/alerts/*\nopendistro_security_anonymous_role:\n  reserved: true\n  cluster_permissions:\n    - cluster:monitor/state\n    - cluster:monitor/health\n    - cluster:monitor/nodes/info\n  index_permissions:\n    - index_patterns:\n        - .kibana\n        - .kibana-6\n        - .kibana_*\n        - .opensearch_dashboards\n        - .opensearch_dashboards-6\n        - .opensearch_dashboards_*\n      allowed_actions:\n        - read\n    - index_patterns:\n        - .tasks\n        - .management-beats\n        - '*:.tasks'\n        - '*:.management-beats'\n      allowed_actions:\n        - read\n    - index_patterns:\n        - opensearch_dashboards_sample_data_logs\n        - opensearch_dashboards_sample_data_flights\n        - opensearch_dashboards_sample_data_ecommerce\n      allowed_actions:\n        - read\n    - index_patterns:\n        - '*'\n      allowed_actions:\n        - read\n        - indices:data/read/mget\n        - indices:data/read/msearch\n        - indices:data/read/mtv\n        - indices:admin/get\n        - indices:admin/aliases/exists*\n        - indices:admin/aliases/get*\n        - indices:admin/mappings/get\n        - indices:data/read/scroll\n        - indices:monitor/settings/get\n        - indices:monitor/stats\n  tenant_permissions:\n    - tenant_patterns:\n        - global_tenant\n      allowed_actions:\n        - kibana_all_read\n\" > opensearch/config/opensearch-security/roles.yml",
              cwd: '/home/ec2-user',
              ignoreErrors: false,
            },
            '013': {
              command: 'set -ex; echo "_meta:\n  type: internalusers\n  config_version: 2\nadmin:\n  hash: \\$2y\\$12\\$fkypbXL0jRI5T25GNBJB3uhPnixWJVPGhFGIQoIaoWuUAQzzOfe3G\n  reserved: true\n  backend_roles:\n    - admin\n  description: Admin user with customized password\nkibanaserver:\n  hash: \\$2y\\$12\\$t17cD/p.ZlsR2jOav7fYfuzk0sWrq1GXZihq3eWsbqXheSJk8Nr2O\n  reserved: true\n  description: OpenSearch Dashboards user with customized password\nkibanaro:\n  hash: \\$2a\\$12\\$JJSXNfTowz7Uu5ttXfeYpeYE0arACvcwlPBStB1F.MI7f0U9Z4DGC\n  reserved: false\n  backend_roles:\n    - kibanauser\n    - readall\n  attributes:\n    attribute1: value1\n    attribute2: value2\n    attribute3: value3\n  description: Demo read-only user for OpenSearch dashboards\nreadall:\n  hash: \\$2a\\$12\\$ae4ycwzwvLtZxwZ82RmiEunBbIPiAmGZduBAjKN0TXdwQFtCwARz2\n  reserved: false\n  backend_roles:\n    - readall\n  description: Demo readall user\n" > opensearch/config/opensearch-security/internal_users.yml',
              cwd: '/home/ec2-user',
              ignoreErrors: false,
            },
            '017': {
              command: "set -ex;cd opensearch-dashboards/config; echo \"opensearch_security.auth.anonymous_auth_enabled: 'true'\nopensearch.password: undefined\nopensearch_security.cookie.secure: 'true'\nopensearch_security.cookie.isSameSite: None\n\">additionalOsdConfig.yml; yq eval-all -i '. as $item ireduce ({}; . * $item)' opensearch_dashboards.yml additionalOsdConfig.yml -P",
              cwd: '/home/ec2-user',
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
  // WHEN
  try {
  // WHEN
    const nightlyStack = new NightlyPlaygroundStack(app, '2x', {
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

test('Test commons stack resources', () => {
  const app = new App({
    context: {
      distVersion: '2.3.0',
      distributionUrl: 'someUrl',
      dashboardsUrl: 'someUrl',
    },
  });

  // WHEN
  const nightlyStack = new NightlyPlaygroundStack(app, '2x', {
    env: { account: 'test-account', region: 'us-east-1' },
  });

  // THEN
  const commonsStack = nightlyStack.stacks.filter((s) => s.stackName === 'commonsStack')[0];
  const commonsStackTemplate = Template.fromStack(commonsStack);

  commonsStackTemplate.hasResourceProperties('AWS::Route53::HostedZone', {
    Name: 'playground.nightly.opensearch.org.',
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
    },
  });

  // WHEN
  const nightlyStack = new NightlyPlaygroundStack(app, '2x', {
    env: { account: 'test-account', region: 'us-east-1' },
  });

  expect(nightlyStack.stacks).toHaveLength(3);
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
