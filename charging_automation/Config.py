# Charging Automation Config

import json


class Config:
    def __init__(self, config_file):
        self.config_file = config_file
        self.rivian_user = None
        self.rivian_pass = None
        self.enphase_token = None
        self.enphase_gateway_sn = None
        self.enphase_gateway_host = None
        self.night_time_start = None
        self.night_time_end = None

        with open(self.config_file) as f:
            data = json.load(f)
            self.rivian_user = data['rivian-user']
            self.rivian_pass = data['rivian-pass']
            self.enphase_token = data['enphase-token']
            self.enphase_gateway_sn = data['enphase-gateway-sn']
            self.enphase_gateway_host = data['enphase-gateway-host']
            self.night_time_start = data['night-time-start']
            self.night_time_end = data['night-time-end']
