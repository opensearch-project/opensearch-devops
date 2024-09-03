import {Construct} from "constructs";
import {JsonSchemaType, Model, RestApi} from "aws-cdk-lib/aws-apigateway";

export class RequestResponseModels{
    public readonly benchmarkJobRequestModel: Model;
    public readonly benchmarkEndpointRequestModel: Model;

    constructor(scope: Construct, restApi: RestApi) {
        this.benchmarkEndpointRequestModel = new Model(scope, 'benchmarkEndpointModel', {
            restApi: restApi,
            modelName: 'benchmarkEndpointRequestModel',
            schema: {
                type: JsonSchemaType.OBJECT,
                properties: {
                    'CLUSTER_ENDPOINT': {type: JsonSchemaType.STRING},
                    'SECURITY_ENABLED': {type: JsonSchemaType.STRING},
                    'USERNAME': {type: JsonSchemaType.STRING},
                    'PASSWORD': {type: JsonSchemaType.STRING},
                    'TEST_WORKLOAD': {type: JsonSchemaType.STRING,
                        enum: ['nyc_taxis', 'http_logs', 'percolator', 'pmc', 'so']},
                    'USER_TAGS': {type: JsonSchemaType.STRING},
                    'WORKLOAD_PARAMS': {type: JsonSchemaType.OBJECT},
                    'TEST_PROCEDURE': {type: JsonSchemaType.STRING},
                    'EXCLUDE_TASKS': {type: JsonSchemaType.STRING},
                    'INCLUDE_TASKS': {type: JsonSchemaType.STRING}
                },
                required: ['CLUSTER_ENDPOINT']
            }
        });

        this.benchmarkJobRequestModel = new Model(scope, 'benchmarkJobRequestModel', {
            restApi: restApi,
            modelName: 'benchmarkJobRequestModel',
            schema: {
                type: JsonSchemaType.OBJECT,
                properties: {
                    'DISTRIBUTION_URL': {type: JsonSchemaType.STRING},
                    'DISTRIBUTION_VERSION': {type: JsonSchemaType.STRING},
                    'SECURITY_ENABLED': {type: JsonSchemaType.STRING},
                    'SINGLE_NODE_CLUSTER': {type: JsonSchemaType.STRING},
                    'MIN_DISTRIBUTION': {type: JsonSchemaType.STRING},
                    'MANAGER_NODE_COUNT': {type: JsonSchemaType.STRING},
                    'DATA_NODE_COUNT': {type: JsonSchemaType.STRING},
                    'CLIENT_NODE_COUNT': {type: JsonSchemaType.STRING},
                    'INGEST_NODE_COUNT': {type: JsonSchemaType.STRING},
                    'ML_NODE_COUNT': {type: JsonSchemaType.STRING},
                    'DATA_INSTANCE_TYPE': {type: JsonSchemaType.STRING},
                    'DATA_NODE_STORAGE': {type: JsonSchemaType.STRING},
                    'ML_NODE_STORAGE': {type: JsonSchemaType.STRING},
                    'JVM_SYS_PROPS': {type: JsonSchemaType.STRING},
                    'USE_50_PERCENT_HEAP': {type: JsonSchemaType.STRING},
                    'TEST_WORKLOAD': {type: JsonSchemaType.STRING,
                        enum: ['nyc_taxis', 'http_logs', 'percolator', 'pmc', 'so']},
                    'USER_TAGS': {type: JsonSchemaType.STRING},
                    'WORKLOAD_PARAMS': {type: JsonSchemaType.OBJECT},
                    'TEST_PROCEDURE': {type: JsonSchemaType.STRING},
                    'EXCLUDE_TASKS': {type: JsonSchemaType.STRING},
                    'INCLUDE_TASKS': {type: JsonSchemaType.STRING},
                    'CAPTURE_NODE_STAT': {type: JsonSchemaType.STRING},
                    'pull_request_number': {type: JsonSchemaType.STRING, default: ''},
                    'repository': {type: JsonSchemaType.STRING, default: ''}
                },
                required: ['DISTRIBUTION_URL', 'DISTRIBUTION_VERSION']
            }
        });
    }
}
