# Run this script to initialize the Rivian API session that uses two factor
# authentication.
# Reads username and password from credentials.json and writes the session info
# to rivian-session.json

import json
import requests
import uuid

GATEWAY_URL = 'https://rivian.com/api/gql/gateway/graphql'
CREDENTIALS_FILE = 'charging_automation/credentials.json'
SESSION_FILE = 'charging_automation/rivian-session.json'


def initialize_session():
    print('Initializing new Rivian session...')
    request = {
        "operationName": "CreateCSRFToken",
        "variables": [],
        "query": "mutation CreateCSRFToken { createCsrfToken { __typename csrfToken appSessionToken } }"
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(GATEWAY_URL, headers=headers, json=request)

    if response.status_code != 200:
        print('Failed to make GraphQL request: {}'.format(response.text))
        return

    data = response.json()
    csrf_token = data['data']['createCsrfToken']['csrfToken']
    app_session_token = data['data']['createCsrfToken']['appSessionToken']

    with open(CREDENTIALS_FILE) as f:
        data = json.load(f)
        username = data['rivian-user']
        password = data['rivian-pass']

    request = {
        "operationName": "Login",
        "variables": {
            "email": username,
            "password": password
        },
        "query": "mutation Login($email: String!, $password: String!) { login(email: $email, password: $password) { __typename ... on MobileLoginResponse { __typename accessToken refreshToken userSessionToken } ... on MobileMFALoginResponse { __typename otpToken } } }"
    }
    headers = {
        'a-sess': app_session_token,
        'csrf-token': csrf_token,
        "Dc-Cid": f"m-ios-{uuid.uuid4()}",
        "User-Agent": "RivianApp/1304 CFNetwork/1404.0.5 Darwin/22.3.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Apollographql-Client-Name": "com.rivian.ios.consumer-apollo-ios",
    }
    response = requests.post(GATEWAY_URL, headers=headers, json=request)

    if response.status_code != 200:
        print('Failed to make GraphQL request: {}'.format(response.text))
        return

    data = response.json()
    otp_token = data['data']['login']['otpToken']

    # OTP code should be sent to email/sms now
    otp_code = input("Enter Authentication Code: ")

    request = {
        "operationName": "LoginWithOTP",
        "variables": {
            "email": username,
            "otpCode": otp_code,
            "otpToken": otp_token
        },
        "query": "mutation LoginWithOTP($email: String!, $otpCode: String!, $otpToken: String!) { loginWithOTP(email: $email, otpCode: $otpCode, otpToken: $otpToken) { __typename accessToken refreshToken userSessionToken } }"
    }
    headers = {
        'a-sess': app_session_token,
        'csrf-token': csrf_token,
        "User-Agent": "RivianApp/1304 CFNetwork/1404.0.5 Darwin/22.3.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Apollographql-Client-Name": "com.rivian.ios.consumer-apollo-ios",
    }
    response = requests.post(GATEWAY_URL, headers=headers, json=request)

    if response.status_code != 200:
        print('Failed to make GraphQL request: {}'.format(response.text))
        return

    data = response.json()
    user_session_token = data['data']['loginWithOTP']['userSessionToken']

    print('Persisting Rivian session')
    with open(SESSION_FILE, 'w') as f:
        session_json = {
            'appSessionToken': app_session_token,
            'userSessionToken': user_session_token,
            'csrfToken': csrf_token
        }
        json.dump(session_json, f)

    print('Rivian session initialized')


initialize_session()
