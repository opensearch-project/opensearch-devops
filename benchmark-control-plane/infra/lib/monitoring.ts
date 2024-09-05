import { StackProps, Duration, Stack } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Method, RestApi } from 'aws-cdk-lib/aws-apigateway';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Alarm,
  ComparisonOperator,
  MathExpression,
  Stats,
  TreatMissingData,
} from 'aws-cdk-lib/aws-cloudwatch';

export interface monitorInterface extends StackProps{
    restApi: RestApi,
    lambdaFunctions: PythonFunction[],
}

export class Monitoring extends Stack {
    private cloudwatchAlarms: Alarm[]

    constructor(scope: Construct, id: string, props:monitorInterface) {
      super(scope, id, props);
      const operations = [
        {
          apiResource: '/submitBenchmarkRun',
          apiMethod: 'POST',
          name: 'submitBenchmarkRun',
        },
        {
          apiResource: '/submitBenchmarkEndpointRun',
          apiMethod: 'POST',
          name: 'submitBenchmarkEndpointRun',
        },
      ];

      operations.forEach((operation) => {
        const dimensionsMap = {
          ApiName: props.restApi.restApiName,
          Stage: props.restApi.deploymentStage.stageName,
          Resource: operation.apiResource,
          Method: operation.apiMethod,
        };

        const errorRateMetric = new MathExpression({
          expression: 'rate*100',
          usingMetrics: {
            rate: props.restApi.metricClientError({
              dimensionsMap,
              statistic: Stats.AVERAGE,
            }),
          },
          period: Duration.minutes(1),
          label: `${operation.name} 4XX Rates`,
        });

        const faultRateMetric = new MathExpression({
          expression: 'rate*100',
          usingMetrics: {
            rate: props.restApi.metricServerError({
              dimensionsMap,
              statistic: Stats.AVERAGE,
            }),
          },
          period: Duration.minutes(1),
          label: `${operation.name} 5XX Rates`,
        });

        const errorRateAlarm = new Alarm(this, `ApiGatewayErrorRateAlarm-${operation.name}`, {
          metric: errorRateMetric,
          evaluationPeriods: 5,
          threshold: 0.5,
          comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
          treatMissingData: TreatMissingData.NOT_BREACHING,
        });

        const faultRateAlarm = new Alarm(this, `ApiGatewayFaultRateAlarm-${operation.name}`, {
          metric: faultRateMetric,
          evaluationPeriods: 5,
          threshold: 5,
          comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
          // For services with multiple operations, it may be okay for one operation
          // not to be called in a long period.
          treatMissingData: TreatMissingData.NOT_BREACHING,
        });
      });

      props.lambdaFunctions.forEach((func) => {
        const lambdaFuncErrorCount = new Alarm(this, `${func.node.id}-LambdaFunctionErrorCountAlarm`, {
          evaluationPeriods: 1,
          threshold: 1,
          metric: func.metricErrors({
            period: Duration.minutes(1),
          }),
          alarmName: `${func.node.id}-LambdaFunctionErrorCount`,
        });
      });
    }
}
