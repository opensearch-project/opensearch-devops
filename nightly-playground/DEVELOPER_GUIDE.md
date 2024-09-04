<!-- TOC -->

- [Developer Guide](#developer-guide)
- [Getting Started](#getting-started)
- [Deployment](#deployment)
    - [Required context parameters](#required-context-parameters)
    - [Sample command to set up multi-node cluster with security enabled](#sample-command-to-set-up-multi-node-cluster-with-security-enabled)

<!-- /TOC -->

## Developer Guide

This project is an extension of [opensearch-cluster-cdk](https://github.com/opensearch-project/opensearch-cluster-cdk) that deploys nightly built artifacts daily. The source code concentrates on taking care of regular deployments, permissions, access, etc. For more customization, please feel free to directly use [opensearch-cluster-cdk](https://github.com/opensearch-project/opensearch-cluster-cdk).

## Getting Started

- Requires [NPM](https://docs.npmjs.com/cli/v7/configuring-npm/install) to be installed
- Install project dependencies using `npm install` from this project directory
- Configure [aws credentials](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html#getting_started_prerequisites)

## Deployment

### Required context parameters

In order to deploy the stack the user needs to provide a set of required parameters listed below:

| Name                          | Requirement | Type      | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|-------------------------------|:------------|:------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| distVersion                   | Required    | string      | The OpenSearch distribution version (released/un-released) the user wants to deploy |
| distributionUrl               | Required    | string      | OpenSearch tarball distribution URL plugin |
| dashboardsUrl                 | Required    | string      | OpenSearch-Dashboards tarball distribution URL version |
| adminPassword                 | Required    | string      | OpenSearch and OpenSearch-Dashboards admin password |
| dashboardPassword             | Required    | string      | OpenSearch-Dashboards password for kibanaserver user |
| dashboardOpenIDClientSecret   | Required    | string      | OpenSearch-Dashboards client secret for OpenID Connect |

### Sample command to set up multi-node cluster with security enabled

```
npm run cdk deploy "*" -- -c distVersion=2.3.0 -c distributionUrl=https://ci.opensearch.org/ci/dbc/distribution-build-opensearch/2.3.0/latest/linux/x64/tar/dist/opensearch/opensearch-2.3.0-linux-x64.tar.gz -c dashboardsUrl=https://ci.opensearch.org/ci/dbc/distribution-build-opensearch-dashboards/2.3.0/latest/linux/x64/tar/dist/opensearch-dashboards/opensearch-dashboards-2.3.0-linux-x64.tar.gz
```