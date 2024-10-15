# CDK for deploying Keycloak

Using this project you can deploy keycloak as a service on AWS.

## Getting Started

- Requires [NPM](https://docs.npmjs.com/cli/v7/configuring-npm/install) to be installed
- Install project dependencies using `npm install` from this project directory
- Configure [aws credentials](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html#getting_started_prerequisites)


* Ensure that your AWS CLI is correctly configured with access credentials.
* Also ensure that you're running these commands in the current directory
* Next, install the required dependencies:

```
npm install
```

## Useful commands

`npm run cdk deploy *`  deploys below stacks to your default AWS account/region:

* keycloakVPC - Deploys networking resources.
* KeyCloakUtils - Deploys utility stack that contains resources such as hosted zone, secrets, certificates, etc.
* KeycloakRDS - Deploys RDS related resources.
* PublicKeycloak - Deploys keycloak using docker image with admin interface disabled.
* InternalKeycloak (optional) - Deploys internally facing keycloak with admin interface enabled.
* KeycloakWAFstack - Deploys stacks containing WAF rules and attached to load balancer(s).

