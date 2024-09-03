
import * as cdk from 'aws-cdk-lib';
import {BenchmarkRestApiStack} from "../lib/restApi";
import {Monitoring} from "../lib/monitoring";

const app = new cdk.App();

const infraStack = new BenchmarkRestApiStack(app, 'benchmark-control-plane-stack', {
    env: {
        region: 'us-east-1',
        account: process.env.CDK_DEFAULT_ACCOUNT
    },
});

const monitoringStack = new Monitoring(app, 'benchmark-cp-monitor-stack', {
    env: {
        region: 'us-east-1',
        account: process.env.CDK_DEFAULT_ACCOUNT
    },
    restApi: infraStack.getRestApi(),
    lambdaFunctions: infraStack.lambdaObject.getLambdaFunctions()
});

monitoringStack.addDependency(infraStack);

