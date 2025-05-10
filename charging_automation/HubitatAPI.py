# Hubitat API

import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class HubitatAPI:
    DEVICE_INFO_URL = '{}/apps/api/{}/devices/{}?access_token={}'
    SET_VARIABLE_URL = '{}/apps/api/{}/devices/{}/setVariable/{}?access_token={}'

    def __init__(self, config_file):
        with open(config_file) as f:
            data = json.load(f)
            self.host = data['host']
            self.api_id = data['api-id']
            self.token = data['token']
            self.on_switch_id = data['automation-on-switch-id']
            self.night_charge_switch_id = data['night-charge-switch-id']
            self.info_device_id = data['info-device-id']

    def get_switch_attribute(self, device_id, attribute):
        url = self.DEVICE_INFO_URL.format(self.host, self.api_id, device_id, self.token)

        logger.info('Reading switch ({}) state from Hubitat'.format(device_id))
        response = requests.get(url)

        if response.status_code != 200:
            logger.error('Failed to make Hubitat request: {}'.format(response.text))
            return

        data = response.json()
        value = None
        for attr in data['attributes']:
            if attr['name'] == attribute:
                value = attr['currentValue']

        return value

    def get_switch_state(self, device_id):
        return self.get_switch_attribute(device_id, attribute='switch')

    def is_automation_on(self):
        state = self.get_switch_state(self.on_switch_id)
        return state == 'on'

    def is_night_charging_on(self):
        state = self.get_switch_state(self.night_charge_switch_id)
        return state == 'on'

    def get_night_charging_limit(self):
        limit = self.get_switch_attribute(self.night_charge_switch_id, attribute='level')
        return limit

    def set_info_message(self, msg, amps, grid):
        current_messages = self.get_switch_attribute(self.info_device_id, attribute='variable').split("\n")

        time = datetime.now()
        message = '{} -- Amps: {} -- Grid: {}W -- Last update: {}'.format(
            msg,
            amps,
            round(grid),
            time.strftime("%Y-%m-%d %H:%M")
        )

        # Show up to 5 changes
        messages_to_show = 5
        compare_chars = 15
        if message[:compare_chars] == current_messages[-1][:compare_chars]:
            # Same message, keep the latest
            current_messages[-1] = message
        else:
            # Message changed
            current_messages.append(message)
        if len(current_messages) > messages_to_show:
            current_messages.pop(0)

        self.update_info_device_message("\n".join(current_messages))

    def update_info_device_message(self, message):
        url = self.SET_VARIABLE_URL.format(self.host, self.api_id, self.info_device_id, message, self.token)

        logger.info('Sending info to Hubitat')
        response = requests.get(url)

        if response.status_code != 200:
            logger.error('Failed to make Hubitat request: {}'.format(response.text))

