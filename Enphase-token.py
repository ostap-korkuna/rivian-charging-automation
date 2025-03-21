# Run this script to get an auth token from Enphase
# Update your username, password and gateway SN below before running
# Copy the resulting token to config.json
from enphase_api.cloud.authentication import Authentication

username = 'my-enphase-user'
password = 'my-enphase-pass'
gatewaySerial = 'my-enphase-gateway-sn'

# Authenticate with Enphase's authentication server and get a token.
authentication = Authentication()
authentication.authenticate(username, password)
token = authentication.get_token_for_commissioned_gateway(gatewaySerial)
print(token)
