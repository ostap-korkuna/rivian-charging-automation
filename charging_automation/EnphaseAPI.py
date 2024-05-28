# Enphase utils

import logging
import json
import os.path
import time

from enphase_api.cloud.authentication import Authentication
from enphase_api.local.gateway import Gateway

logger = logging.getLogger(__name__)


def get_secure_gateway_session(credentials):
    """
    Establishes a secure session with the Enphase® IQ Gateway API.

    This function manages the authentication process to establish a secure session with
    an Enphase® IQ Gateway.

    It handles JWT validation, token acquisition (if required) and initialises
    the Gateway API wrapper for subsequent interactions.

    It also downloads and stores the certificate from the gateway for secure communication.

    Args:
        credentials (dict): A dictionary containing the required credentials.

    Returns:
        Gateway: An initialised Gateway API wrapper object for interacting with the gateway.

    Raises:
        ValueError: If authentication fails or if required credentials are missing.
    """

    # Do we have a valid JSON Web Token (JWT) to be able to use the service?
    if not (credentials.get('enphase-token')
                and Authentication.check_token_valid(
                    token=credentials['enphase-token'],
                    gateway_serial_number=credentials.get('enphase-gateway-sn'))):
        # It is not valid so clear it.
        credentials['enphase-token'] = None

    # Do we still not have a Token?
    if not credentials.get('enphase-token'):
        # Do we have a way to obtain a token?
        if credentials.get('enphase-user') and credentials.get('enphase-pass'):
            # Create a Authentication object.
            authentication = Authentication()

            # Authenticate with Entrez (French for "Access").
            if not authentication.authenticate(
                username=credentials['enphase-user'],
                password=credentials['enphase-pass']):
                raise ValueError('Failed to login to Enphase® Authentication server ("Entrez")')

            # Does the user want to target a specific gateway or all uncommissioned ones?
            if credentials.get('enphase-gateway-sn'):
                # Get a new gateway specific token (installer = short-life, owner = long-life).
                credentials['enphase-token'] = authentication.get_token_for_commissioned_gateway(
                    gateway_serial_number=credentials['enphase-gateway-sn']
                )
            else:
                # Get a new uncommissioned gateway specific token.
                credentials['enphase-token'] = authentication.get_token_for_uncommissioned_gateway()

            # Update the file to include the modified token.
            with open('credentials.json', mode='w', encoding='utf-8') as json_file:
                json.dump(credentials, json_file, indent=4)
        else:
            # Let the user know why the program is exiting.
            raise ValueError('Unable to login to the gateway (bad, expired or missing token in credentials.json).')

    # Did the user override the library default hostname to the Gateway?
    host = credentials.get('enphase-gateway-host')

    # Download and store the certificate from the gateway so all future requests are secure.
    if not os.path.exists('gateway.cer'):
        Gateway.trust_gateway(host)

    # Instantiate the Gateway API wrapper (with the default library hostname if None provided).
    gateway = Gateway(host)

    # Are we not able to login to the gateway?
    if not gateway.login(credentials['enphase-token']):
        # Let the user know why the program is exiting.
        raise ValueError('Unable to login to the gateway (bad, expired or missing token in credentials.json).')

    # Return the initialised gateway object.
    return gateway


class EnphaseAPI:
    def __init__(self, credentials_file):
        self.credentials_file = credentials_file
        self.gateway = self.enphase_gateway()

    def enphase_gateway(self):
        with open(self.credentials_file, 'r') as f:
            credentials = json.load(f)
        return get_secure_gateway_session(credentials)

    def read_stats(self):
        production_statistics = self.gateway.api_call('/production.json')
        production = total_consumption = net_consumption = reading_time = 0
        for record in production_statistics['production']:
            if record['type'] == 'eim' and record['measurementType'] == 'production':
                production = record['wNow']
                reading_time = record['readingTime']
        for record in production_statistics['consumption']:
            if record['type'] == 'eim' and record['measurementType'] == 'total-consumption':
                total_consumption = record['wNow']
            if record['type'] == 'eim' and record['measurementType'] == 'net-consumption':
                net_consumption = record['wNow']
        battery = production_statistics['storage'][0]['wNow']
        return {
            'reading_time': reading_time,
            'production': production,
            'total_consumption': total_consumption,
            'net_consumption': net_consumption,
            'battery': battery
        }

    def live_stats_enable(self):
        self.gateway.api_call('/ivp/livedata/stream', method='POST', json={"enable": 1})

    def live_stats_disable(self):
        self.gateway.api_call('/ivp/livedata/stream', method='POST', json={"enable": 0})

    def read_live_stats(self):
        livedata = self.gateway.api_call('/ivp/livedata/status')
        production = livedata['meters']['pv']['agg_p_mw'] / 1000
        consumption = livedata['meters']['load']['agg_p_mw'] / 1000
        grid = livedata['meters']['grid']['agg_p_mw'] / 1000
        battery = livedata['meters']['storage']['agg_p_mw'] / 1000
        reading_time = livedata['meters']['last_update']
        return {
            'reading_time': reading_time,
            'production': production,
            'consumption': consumption,
            'grid': grid,
            'battery': battery
        }

    def get_median_grid_consumption(self, include_battery_usage=True):
        logger.info('Getting median consumption from Enphase')
        # Read 5 times with 10 secs in between. Take the median
        num_readings = 5
        grid_readings = []
        # Enable live stats MQTT streaming, otherwise the values will stop updating after 10 minutes
        self.live_stats_enable()
        for i in range(num_readings):
            logger.info('Reading consumption from Enphase {} / {}'.format(i + 1, num_readings))
            # Sleep before the read to allow data to accumulate
            time.sleep(10)
            stats = self.read_live_stats()
            logger.info('Live Stats: {}'.format(stats))
            stats_2 = self.read_stats()
            logger.info('Prod Stats: {}'.format(stats_2))
            consumption = stats['grid']
            # Only include battery usage, but ignore battery charging (i.e. let it charge)
            if include_battery_usage and stats['battery'] > 0:
                consumption += stats['battery']
            grid_readings.append(consumption)
        # Disable live stats MQTT streaming
        self.live_stats_disable()
        return sorted(grid_readings)[num_readings // 2]  # median
