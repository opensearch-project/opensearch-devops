import {Construct} from "constructs";
import {PythonFunction} from "@aws-cdk/aws-lambda-python-alpha";
import * as python from "@aws-cdk/aws-lambda-python-alpha";
import * as path from "node:path";
import {Runtime} from "aws-cdk-lib/aws-lambda";
import * as cdk from "aws-cdk-lib";
import {Secret} from "aws-cdk-lib/aws-secretsmanager";

export class BenchmarkLambdaFunctions{
    public readonly benchmarkLambda: PythonFunction;
    public readonly customAuthorizerLambda: PythonFunction;
    private lambdaFunctions: PythonFunction[] = [];

    constructor(scope: Construct){
        const benchmarkJobToken = new Secret(scope, 'benchmarkJobToken', {
            secretName: 'benchmark-job-token'
        });

        const benchmarkEndpointJobToken = new Secret(scope, 'benchmarkEndpointJobToken', {
            secretName: 'benchmark-endpoint-job-token'
        });

        const github_app_id = new Secret(scope, 'githubAppId', {
            secretName: 'app_id'
        });
        const github_installation_id = new Secret(scope, 'githubInstallationId', {
            secretName: 'installation_id'
        });
        const github_private_key = new Secret(scope, 'githubPrivateKey', {
            secretName: 'private_key'
        });

        this.benchmarkLambda = new python.PythonFunction(scope, 'submitJenkinsJob', {
            functionName: 'submit-benchmark-run',
            entry: path.join(__dirname,'../lambda'),
            runtime: Runtime.PYTHON_3_10,
            index: 'submit_jenkins_job.py',
            handler: 'handler',
            timeout:  cdk.Duration.seconds(300),
        });
        benchmarkJobToken.grantRead(this.benchmarkLambda);
        benchmarkEndpointJobToken.grantRead(this.benchmarkLambda);
        this.lambdaFunctions.push(this.benchmarkLambda)

        this.customAuthorizerLambda = new python.PythonFunction(scope, 'authorizer-lambda', {
            functionName: 'custom-lambda-authorizer',
            entry: path.join(__dirname, '../lambda'),
            runtime: Runtime.PYTHON_3_10,
            index: 'custom_lambda_auth.py',
            handler: 'lambda_handler',
            timeout: cdk.Duration.seconds(300)
        });

        github_app_id.grantRead(this.customAuthorizerLambda);
        github_installation_id.grantRead(this.customAuthorizerLambda);
        github_private_key.grantRead(this.customAuthorizerLambda);

        this.lambdaFunctions.push(this.customAuthorizerLambda)
    }

    public getLambdaFunctions(): PythonFunction[] {
        return this.lambdaFunctions
    }
}
