import json
from datetime import datetime, timedelta, timezone

import boto3
import requests
from botocore.exceptions import ClientError
from jwt import (JWT,
                 jwk_from_dict,
                 jwk_from_pem)
from jwt.utils import get_int_from_datetime


def lambda_handler(event, context):
    # Get the authorization header from the event
    auth_header = event.get('authorizationToken')

    # Check if the authorization header is present
    if auth_header:
        access_token = auth_header

        try:
            # Verify the access token with GitHub
            headers = {'Authorization': f'token {access_token}'}
            response = requests.get('https://api.github.com/user', headers=headers)
            response.raise_for_status()  # Raise an exception for non-2xx status codes
            is_authorized = check_user_permission(response.json()['login'])

            if response.status_code == 200 and is_authorized:
                # Access token is valid, generate a policy document to allow the request
                print(f"User {response.json()['login']} is authorized")
                policy = generate_policy(event['methodArn'], 'Allow', response.json()['login'])
                return policy
            else:
                print(f"User {response.json()['login']} is not authorized.")
                # Generate a policy document to deny the request
                policy = generate_policy(event['methodArn'], 'Deny', response.json()['login'])
                return policy

        except requests.exceptions.RequestException as e:
            print(f"Error occurred while verifying access token: {e}")
            # Generate a policy document to deny the request
            policy = generate_policy(event['methodArn'], 'Deny', 'user')
            return policy

    else:
        print("No authorization header, generate a policy document to deny the request")
        # No authorization header, generate a policy document to deny the request
        policy = generate_policy(event['methodArn'], 'Deny', 'user')
        return policy


def get_secret(secret_name):
    region = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    return secret


def generate_policy(method_arn, effect, principal_id):
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': method_arn
                }
            ]
        }
    }
    return policy


def check_user_permission(user_name):
    app_id = get_secret('app_id')
    installation_id = get_secret('installation_id')
    private_key = get_secret('private_key')

    signing_key = jwk_from_pem(private_key.encode('utf-8'))
    instance = JWT()

    message = {
        'iss': app_id,
        'iat': get_int_from_datetime(datetime.now(timezone.utc)),
        'exp': get_int_from_datetime(
            datetime.now(timezone.utc) + timedelta(minutes=10))
    }

    jwt_token = instance.encode(message, signing_key, alg='RS256')

    url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    response = requests.post(url, headers=headers)
    installation_token = response.json()['token']

    api_url = f'https://api.github.com/orgs/opensearch-project/teams/submit-benchmark/memberships/{user_name}'
    headers = {
        'Authorization': f'Bearer {installation_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        return False

    return True
