import boto3
from botocore.exceptions import ClientError
import requests
import json
import jenkins
import time


def handler(event, context):
    resource = event.get('resource')

    if 'submitBenchmarkRun' in resource:
        secret_name = 'benchmark-job-token'
        jenkins_job_name = 'zsngri-gradle-test'
    elif 'submitBenchmarkEndpointRun' in resource:
        secret_name = 'benchmark-endpoint-job-token'
        jenkins_job_name = 'zsngri-gradle-test'

    job_token = get_secret(secret_name)

    jenkins_url = 'https://build.ci.opensearch.org'
    webhook_url = f"{jenkins_url}/generic-webhook-trigger/invoke"
    headers = {
        "Authorization": f"Bearer {job_token}",
        "Content-Type": "application/json"
    }

    data = json.loads(event.get('body', ''))
    print(f"Event is {event}")

    if 'pull_request_number' not in data.keys():
        data['pull_request_number'] = 'null'
    if 'repository' not in data.keys():
        data['repository'] = 'null'

    try:
        response = requests.post(webhook_url, headers=headers, json=data, timeout=300)
    except Exception as e:
        print(f"Error in sending request to jenkins:{e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {e}. Something went wrong, please contact engineering-effectiveness team.")
        }

    json_response = response.json()
    print(f"Job data is {json_response.get('jobs')}")
    queue_id = json_response.get('jobs').get(jenkins_job_name).get('id')

    client = jenkins.Jenkins(url=jenkins_url, timeout=300)
    while True:
        queue_info = client.get_queue_item(queue_id)
        if queue_info['why'] is None:
            print(f"The job url is {queue_info['executable']['url']}")
            break
        print("Waiting for Job to execute")
        time.sleep(3)

    return {
        'statusCode': 200,
        'body': json.dumps({"job_url": queue_info['executable']['url']})
    }


def get_secret(secret_name):
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    return secret

