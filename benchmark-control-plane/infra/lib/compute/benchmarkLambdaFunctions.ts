import { Construct } from 'constructs';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { join } from 'node:path';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { Duration } from 'aws-cdk-lib';
import { Secret } from 'aws-cdk-lib/aws-secretsmanager';

export class BenchmarkLambdaFunctions {
    public readonly benchmarkLambda: PythonFunction;

    public readonly customAuthorizerLambda: PythonFunction;

    private lambdaFunctions: PythonFunction[] = [];

    constructor(scope: Construct) {
      const benchmarkJobToken = new Secret(scope, 'benchmarkJobToken', {
        secretName: 'benchmark-job-token',
      });

      const benchmarkEndpointJobToken = new Secret(scope, 'benchmarkEndpointJobToken', {
        secretName: 'benchmark-endpoint-job-token',
      });

      const githubAppId = new Secret(scope, 'githubAppId', {
        secretName: 'app_id',
      });
      const githubInstallationId = new Secret(scope, 'githubInstallationId', {
        secretName: 'installation_id',
      });
      const githubPrivateKey = new Secret(scope, 'githubPrivateKey', {
        secretName: 'private_key',
      });

      this.benchmarkLambda = new PythonFunction(scope, 'submitJenkinsJob', {
        functionName: 'submit-benchmark-run',
        entry: join(__dirname, '../lambda'),
        runtime: Runtime.PYTHON_3_10,
        index: 'submit_jenkins_job.py',
        handler: 'handler',
        timeout: Duration.seconds(300),
      });
      benchmarkJobToken.grantRead(this.benchmarkLambda);
      benchmarkEndpointJobToken.grantRead(this.benchmarkLambda);
      this.lambdaFunctions.push(this.benchmarkLambda);

      this.customAuthorizerLambda = new PythonFunction(scope, 'authorizer-lambda', {
        functionName: 'custom-lambda-authorizer',
        entry: join(__dirname, '../lambda'),
        runtime: Runtime.PYTHON_3_10,
        index: 'custom_lambda_auth.py',
        handler: 'lambda_handler',
        timeout: Duration.seconds(300),
      });

      githubAppId.grantRead(this.customAuthorizerLambda);
      githubInstallationId.grantRead(this.customAuthorizerLambda);
      githubPrivateKey.grantRead(this.customAuthorizerLambda);

      this.lambdaFunctions.push(this.customAuthorizerLambda);
    }

    public getLambdaFunctions(): PythonFunction[] {
      return this.lambdaFunctions;
    }
}
