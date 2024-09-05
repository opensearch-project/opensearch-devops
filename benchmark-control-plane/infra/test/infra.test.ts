import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { describe } from 'node:test';
import { BenchmarkRestApiStack } from '../lib/restApi';

describe('Benchmark Control Plane Stack', () => {
  const app = new App({
    context: {
      region: 'us-east-1',
      account: '123456789',
    },
  });
  const stack = new BenchmarkRestApiStack(app, 'benchmark-control-plane-stack');
  const template = Template.fromStack(stack);

  test('Resource count', () => {
    template.resourceCountIs('AWS::SecretsManager::Secret', 5);
    template.resourceCountIs('AWS::Lambda::Function', 2);
    template.resourceCountIs('AWS::ApiGateway::RestApi', 1);
    template.resourceCountIs('AWS::ApiGateway::Resource', 2);
    template.resourceCountIs('AWS::ApiGateway::Model', 2);
    template.resourceCountIs('AWS::ApiGateway::Authorizer', 1);
    template.resourceCountIs('AWS::IAM::Role', 3);
    template.resourceCountIs('AWS::Logs::LogGroup', 1);
  });

  test('Lambda Resource Properties', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'submit-benchmark-run',
      Runtime: 'python3.10',
      Timeout: 300,
      Role: {
        'Fn::GetAtt': [
          'submitJenkinsJobServiceRole2CDF93B0',
          'Arn',
        ],
      },
    });

    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'custom-lambda-authorizer',
      Runtime: 'python3.10',
      Timeout: 300,
      Role: {
        'Fn::GetAtt': [
          'authorizerlambdaServiceRole8AE10C6A',
          'Arn',
        ],
      },
    });
  });

  test('Api Gateway Properties', () => {
    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      ParentId: {
        'Fn::GetAtt': [
          'benchmarkApisAC3C2338',
          'RootResourceId',
        ],
      },
      PathPart: 'submitBenchmarkRun',
      RestApiId: {
        Ref: 'benchmarkApisAC3C2338',
      },
    });

    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      ParentId: {
        'Fn::GetAtt': [
          'benchmarkApisAC3C2338',
          'RootResourceId',
        ],
      },
      PathPart: 'submitBenchmarkEndpointRun',
      RestApiId: {
        Ref: 'benchmarkApisAC3C2338',
      },
    });

    template.hasResourceProperties('AWS::ApiGateway::Model', {
      ContentType: 'application/json',
      Name: 'benchmarkEndpointRequestModel',
      RestApiId: {
        Ref: 'benchmarkApisAC3C2338',
      },
      Schema: {
        type: 'object',
        properties: {
          CLUSTER_ENDPOINT: {
            type: 'string',
          },
          SECURITY_ENABLED: {
            type: 'string',
          },
          USERNAME: {
            type: 'string',
          },
          PASSWORD: {
            type: 'string',
          },
          TEST_WORKLOAD: {
            type: 'string',
            enum: [
              'nyc_taxis',
              'http_logs',
              'percolator',
              'pmc',
              'so',
            ],
          },
          USER_TAGS: {
            type: 'string',
          },
          WORKLOAD_PARAMS: {
            type: 'object',
          },
          TEST_PROCEDURE: {
            type: 'string',
          },
          EXCLUDE_TASKS: {
            type: 'string',
          },
          INCLUDE_TASKS: {
            type: 'string',
          },
        },
        required: [
          'CLUSTER_ENDPOINT',
        ],
        $schema: 'http://json-schema.org/draft-04/schema#',
      },
    });

    template.hasResourceProperties('AWS::ApiGateway::Model', {
      ContentType: 'application/json',
      Name: 'benchmarkJobRequestModel',
      RestApiId: {
        Ref: 'benchmarkApisAC3C2338',
      },
      Schema: {
        type: 'object',
        properties: {
          DISTRIBUTION_URL: {
            type: 'string',
          },
          DISTRIBUTION_VERSION: {
            type: 'string',
          },
          SECURITY_ENABLED: {
            type: 'string',
          },
          SINGLE_NODE_CLUSTER: {
            type: 'string',
          },
          MIN_DISTRIBUTION: {
            type: 'string',
          },
          MANAGER_NODE_COUNT: {
            type: 'string',
          },
          DATA_NODE_COUNT: {
            type: 'string',
          },
          CLIENT_NODE_COUNT: {
            type: 'string',
          },
          INGEST_NODE_COUNT: {
            type: 'string',
          },
          ML_NODE_COUNT: {
            type: 'string',
          },
          DATA_INSTANCE_TYPE: {
            type: 'string',
          },
          DATA_NODE_STORAGE: {
            type: 'string',
          },
          ML_NODE_STORAGE: {
            type: 'string',
          },
          JVM_SYS_PROPS: {
            type: 'string',
          },
          USE_50_PERCENT_HEAP: {
            type: 'string',
          },
          TEST_WORKLOAD: {
            type: 'string',
            enum: [
              'nyc_taxis',
              'http_logs',
              'percolator',
              'pmc',
              'so',
            ],
          },
          USER_TAGS: {
            type: 'string',
          },
          WORKLOAD_PARAMS: {
            type: 'object',
          },
          TEST_PROCEDURE: {
            type: 'string',
          },
          EXCLUDE_TASKS: {
            type: 'string',
          },
          INCLUDE_TASKS: {
            type: 'string',
          },
          CAPTURE_NODE_STAT: {
            type: 'string',
          },
          pull_request_number: {
            type: 'string',
            default: '',
          },
          repository: {
            type: 'string',
            default: '',
          },
        },
        required: [
          'DISTRIBUTION_URL',
          'DISTRIBUTION_VERSION',
        ],
        $schema: 'http://json-schema.org/draft-04/schema#',
      },
    });

    template.hasResourceProperties('AWS::ApiGateway::Authorizer', {
      IdentitySource: 'method.request.header.authorizationToken',
      RestApiId: {
        Ref: 'benchmarkApisAC3C2338',
      },
      Type: 'TOKEN',
    });
  });
});
