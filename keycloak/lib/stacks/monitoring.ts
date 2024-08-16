/**
 * SPDX-License-Identifier: Apache-2.0
 *
 * The OpenSearch Contributors require contributions made to
 * this file be licensed under the Apache-2.0 license or a
 * compatible open source license.
 */

import { AutoScalingGroup } from 'aws-cdk-lib/aws-autoscaling';
import {
  Alarm, AlarmWidget, ComparisonOperator, Dashboard, Metric, TreatMissingData,
} from 'aws-cdk-lib/aws-cloudwatch';
import { ApplicationTargetGroup } from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import { Construct } from 'constructs';

export class KeycloakMonitoring {
    public readonly alarms: Alarm[] = [];

    constructor(scope: Construct, id: string, targetGroup: ApplicationTargetGroup, autoScalingGroup: AutoScalingGroup) {
      const dashboard = new Dashboard(scope, 'AlarmDashboard');

      const cpuMetric = new Metric({
        namespace: 'AWS/EC2',
        metricName: `${id}-CPUUtilization`,
        dimensionsMap: {
          AutoScalingGroupName: autoScalingGroup.autoScalingGroupName,
        },
      });

      this.alarms.push(new Alarm(scope, `${id}-AverageMainNodeCpuUtilization`, {
        alarmDescription: 'Overall EC2 avg CPU Utilization',
        evaluationPeriods: 3,
        metric: cpuMetric,
        threshold: 75,
        comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
      }));

      this.alarms.push(new Alarm(scope, `${id}-ExternalLoadBalancerUnhealthyHosts`, {
        alarmDescription: 'If any hosts behind the load balancer are unhealthy',
        metric: targetGroup.metrics.unhealthyHostCount(),
        evaluationPeriods: 3,
        threshold: 1,
        comparisonOperator: ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: TreatMissingData.BREACHING,
      }));

      this.alarms
        .map((alarm) => new AlarmWidget({ alarm }))
        .forEach((widget) => dashboard.addWidgets(widget));
    }
}
