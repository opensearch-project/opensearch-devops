import * as cdk from 'aws-cdk-lib';
import {RemovalPolicy, Stack} from 'aws-cdk-lib';
import {Construct} from "constructs";
import {
    AccessLogFormat,
    AuthorizationType,
    IdentitySource,
    LambdaIntegration,
    LogGroupLogDestination, Method,
    MethodLoggingLevel,
    RestApi,
    TokenAuthorizer
} from "aws-cdk-lib/aws-apigateway";
import {LogGroup} from "aws-cdk-lib/aws-logs";
import {BenchmarkLambdaFunctions} from "./compute/benchmarkLambdaFunctions";
import {RequestResponseModels} from "./models/requestResponseModels";

export class BenchmarkRestApiStack extends Stack {
    private readonly restApi: RestApi;
    private readonly authorizer: TokenAuthorizer;
    public lambdaObject: BenchmarkLambdaFunctions;

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        this.lambdaObject = new BenchmarkLambdaFunctions(this);

        this.restApi = new RestApi(this, 'benchmarkApis', {
            restApiName: 'benchmarkApis',
            description: 'Apis to submit benchmark related runs',
            cloudWatchRole: true,
            cloudWatchRoleRemovalPolicy: RemovalPolicy.DESTROY,
            deployOptions: {
                stageName: 'dev',
                loggingLevel: MethodLoggingLevel.INFO,
                accessLogDestination: new LogGroupLogDestination(new LogGroup(this, 'api-gateway-log-group', {
                    removalPolicy: RemovalPolicy.DESTROY
                })),
                metricsEnabled: true,
                accessLogFormat: AccessLogFormat.jsonWithStandardFields()
            }
        });

        const apiModels = new RequestResponseModels(this, this.restApi);

        const requestValidator= this.restApi.addRequestValidator('requestValidator', {
            requestValidatorName: 'requestValidator',
            validateRequestBody: true,
            validateRequestParameters: true
        });

        this.authorizer = new TokenAuthorizer(this, 'custom-lambda-authorizer', {
            handler: this.lambdaObject.customAuthorizerLambda,
            identitySource: IdentitySource.header('authorizationToken'),
        });

        const submitBenchmarkApi = this.restApi.root.addResource('submitBenchmarkRun');
        const benchmarkEndpointApi = this.restApi.root.addResource('submitBenchmarkEndpointRun');

        submitBenchmarkApi.addMethod('POST', new LambdaIntegration(this.lambdaObject.benchmarkLambda), {
            requestModels: {
                'application/json': apiModels.benchmarkJobRequestModel
            },
            requestValidator: requestValidator,
            authorizer: this.authorizer,
            authorizationType: AuthorizationType.CUSTOM
        });

        benchmarkEndpointApi.addMethod('POST', new LambdaIntegration(this.lambdaObject.benchmarkLambda), {
            requestModels: {
                'application/json': apiModels.benchmarkEndpointRequestModel
            },
            requestValidator: requestValidator,
            authorizer: this.authorizer,
            authorizationType: AuthorizationType.CUSTOM
        });
    }

    public getRestApi(): RestApi {
        return this.restApi;
    }

}
