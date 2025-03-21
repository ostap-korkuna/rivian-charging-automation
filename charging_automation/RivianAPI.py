# Rivian API wrapper

import logging
import os
import json
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class RivianAPI:
    GATEWAY_URL = 'https://rivian.com/api/gql/gateway/graphql'
    CHARGING_URL = 'https://rivian.com/api/gql/chrg/user/graphql'
    AMPS_MAX = 48
    AMPS_MIN = 8

    def __init__(self, config, session_file):
        self.config = config
        self.session_file = session_file
        self.app_session_token = None
        self.user_session_token = None
        self.csrf_token = None
        self.vehicle_id = None
        self.charging_status = None
        self.battery_level = None
        self.login()
        self.init_vehicle_info()

    def init_session(self):
        # Getting CSRF token
        logger.info('Initializing new Rivian session...')
        request = {
            "operationName": "CreateCSRFToken",
            "variables": [],
            "query": "mutation CreateCSRFToken { createCsrfToken { __typename csrfToken appSessionToken } }"
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.GATEWAY_URL, headers=headers, json=request)

        if response.status_code != 200:
            logger.error('Failed to make GraphQL request: {}'.format(response.text))
            return

        data = response.json()
        self.csrf_token = data['data']['createCsrfToken']['csrfToken']
        self.app_session_token = data['data']['createCsrfToken']['appSessionToken']

        username = self.config.rivian_user
        password = self.config.rivian_pass

        request = {
            "operationName": "Login",
            "variables": {
                "email": username,
                "password": password
            },
            "query": "mutation Login($email: String!, $password: String!) { login(email: $email, password: $password) { __typename ... on MobileLoginResponse { accessToken refreshToken userSessionToken } ... on MobileMFALoginResponse { otpToken } } }"
        }
        headers = {
            'a-sess': self.app_session_token,
            'csrf-token': self.csrf_token,
            'apollographql-client-name': 'com.rivian.android.consumer'
        }
        response = requests.post(self.GATEWAY_URL, headers=headers, json=request)

        if response.status_code != 200:
            logger.error('Failed to make GraphQL request: {}'.format(response.text))
            return

        data = response.json()
        self.user_session_token = data['data']['login']['userSessionToken']
        logger.info('Rivian session initialized')

    def init_user_info(self):
        if not self.app_session_token:
            return False

        logger.info('Loading Rivian user data...')
        request = {
            "operationName": "getUserInfo",
            "variables": {},
            "query": "query getUserInfo { currentUser { __typename id firstName lastName email address { __typename country } vehicles { __typename id name owner roles vin vas { __typename vasVehicleId vehiclePublicKey } vehicle { __typename model mobileConfiguration { __typename trimOption { __typename optionId optionName } exteriorColorOption { __typename optionId optionName } interiorColorOption { __typename optionId optionName } } vehicleState { __typename supportedFeatures { __typename name status } } otaEarlyAccessStatus } settings { __typename name { __typename value } } } enrolledPhones { __typename vas { __typename vasPhoneId publicKey } enrolled { __typename deviceType deviceName vehicleId identityId shortName } } pendingInvites { __typename id invitedByFirstName role status vehicleId vehicleModel email } } }"
        }

        headers = {
            'a-sess': self.app_session_token,
            'u-sess': self.user_session_token,
            'csrf-token': self.csrf_token,
            'apollographql-client-name': 'com.rivian.android.consumer'
        }

        response = requests.post(self.GATEWAY_URL, headers=headers, json=request)

        if response.status_code != 200:
            return False
        data = response.json()
        self.vehicle_id = data['data']['currentUser']['vehicles'][0]['id']
        logger.info('Rivian user data loaded')
        return True

    def init_vehicle_info(self):
        logger.info('Loading Rivian vehicle data...')

        request = {
            "operationName": "GetVehicleState",
            "variables": {
                "vehicleID": self.vehicle_id
            },
            "query": "query GetVehicleState($vehicleID: String!) { vehicleState(id: $vehicleID) { __typename gnssLocation { __typename latitude longitude timeStamp } alarmSoundStatus { __typename timeStamp value } timeToEndOfCharge { __typename timeStamp value } doorFrontLeftLocked { __typename timeStamp value } doorFrontLeftClosed { __typename timeStamp value } doorFrontRightLocked { __typename timeStamp value } doorFrontRightClosed { __typename timeStamp value } doorRearLeftLocked { __typename timeStamp value } doorRearLeftClosed { __typename timeStamp value } doorRearRightLocked { __typename timeStamp value } doorRearRightClosed { __typename timeStamp value } windowFrontLeftClosed { __typename timeStamp value } windowFrontRightClosed { __typename timeStamp value } windowFrontLeftCalibrated { __typename timeStamp value } windowFrontRightCalibrated { __typename timeStamp value } windowRearLeftCalibrated { __typename timeStamp value } windowRearRightCalibrated { __typename timeStamp value } closureFrunkLocked { __typename timeStamp value } closureFrunkClosed { __typename timeStamp value } gearGuardLocked { __typename timeStamp value } closureLiftgateLocked { __typename timeStamp value } closureLiftgateClosed { __typename timeStamp value } windowRearLeftClosed { __typename timeStamp value } windowRearRightClosed { __typename timeStamp value } closureSideBinLeftLocked { __typename timeStamp value } closureSideBinLeftClosed { __typename timeStamp value } closureSideBinRightLocked { __typename timeStamp value } closureSideBinRightClosed { __typename timeStamp value } closureTailgateLocked { __typename timeStamp value } closureTailgateClosed { __typename timeStamp value } closureTonneauLocked { __typename timeStamp value } closureTonneauClosed { __typename timeStamp value } wiperFluidState { __typename timeStamp value } powerState { __typename timeStamp value } batteryHvThermalEventPropagation { __typename timeStamp value } vehicleMileage { __typename timeStamp value } brakeFluidLow { __typename timeStamp value } gearStatus { __typename timeStamp value } tirePressureStatusFrontLeft { __typename timeStamp value } tirePressureStatusValidFrontLeft { __typename timeStamp value } tirePressureStatusFrontRight { __typename timeStamp value } tirePressureStatusValidFrontRight { __typename timeStamp value } tirePressureStatusRearLeft { __typename timeStamp value } tirePressureStatusValidRearLeft { __typename timeStamp value } tirePressureStatusRearRight { __typename timeStamp value } tirePressureStatusValidRearRight { __typename timeStamp value } batteryLevel { __typename timeStamp value } chargerState { __typename timeStamp value } batteryLimit { __typename timeStamp value } remoteChargingAvailable { __typename timeStamp value } batteryHvThermalEvent { __typename timeStamp value } rangeThreshold { __typename timeStamp value } distanceToEmpty { __typename timeStamp value } otaAvailableVersionNumber { __typename timeStamp value } otaAvailableVersionWeek { __typename timeStamp value } otaAvailableVersionYear { __typename timeStamp value } otaCurrentVersionNumber { __typename timeStamp value } otaCurrentVersionWeek { __typename timeStamp value } otaCurrentVersionYear { __typename timeStamp value } otaDownloadProgress { __typename timeStamp value } otaInstallDuration { __typename timeStamp value } otaInstallProgress { __typename timeStamp value } otaInstallReady { __typename timeStamp value } otaInstallTime { __typename timeStamp value } otaInstallType { __typename timeStamp value } otaStatus { __typename timeStamp value } otaCurrentStatus { __typename timeStamp value } cabinClimateInteriorTemperature { __typename timeStamp value } cabinPreconditioningStatus { __typename timeStamp value } cabinPreconditioningType { __typename timeStamp value } petModeStatus { __typename timeStamp value } petModeTemperatureStatus { __typename timeStamp value } cabinClimateDriverTemperature { __typename timeStamp value } gearGuardVideoStatus { __typename timeStamp value } gearGuardVideoMode { __typename timeStamp value } gearGuardVideoTermsAccepted { __typename timeStamp value } defrostDefogStatus { __typename timeStamp value } steeringWheelHeat { __typename timeStamp value } seatFrontLeftHeat { __typename timeStamp value } seatFrontRightHeat { __typename timeStamp value } seatRearLeftHeat { __typename timeStamp value } seatRearRightHeat { __typename timeStamp value } chargerStatus { __typename timeStamp value } seatFrontLeftVent { __typename timeStamp value } seatFrontRightVent { __typename timeStamp value } chargerDerateStatus { __typename timeStamp value } driveMode { __typename timeStamp value } } }"
        }
        headers = {
            'a-sess': self.app_session_token,
            'u-sess': self.user_session_token,
            'csrf-token': self.csrf_token,
            'apollographql-client-name': 'com.rivian.android.consumer'
        }
        response = requests.post(self.GATEWAY_URL, headers=headers, json=request)

        if response.status_code != 200:
            logger.error('Failed to make GraphQL request: {}'.format(response.text))
            return

        data = response.json()

        if data['data']['vehicleState']['chargerStatus'] == None:
            logger.info('Rivian vehicle data missing — might be in service mode')
            return

        self.charging_status = data['data']['vehicleState']['chargerStatus']['value']
        self.battery_level = data['data']['vehicleState']['batteryLevel']['value']
        logger.info('Rivian vehicle data loaded')

    def login(self):
        # check stored session first
        if os.path.exists(self.session_file):
            logger.info('Rivian session found')
            with open(self.session_file) as f:
                data = json.load(f)
                self.app_session_token = data['appSessionToken']
                self.user_session_token = data['userSessionToken']
                self.csrf_token = data['csrfToken']

        # if connection fails, reinitialize
        if not self.init_user_info():
            self.init_session()
            if self.init_user_info():
                # store session for future use
                logger.info('Persisting Rivian session')
                with open(self.session_file, 'w') as f:
                    session_json = {
                        'appSessionToken': self.app_session_token,
                        'userSessionToken': self.user_session_token,
                        'csrfToken': self.csrf_token
                    }
                    json.dump(session_json, f)

    def is_charging(self):
        return self.charging_status == 'chrgr_sts_connected_charging'

    def is_charger_connected(self):
        return self.charging_status in ['chrgr_sts_connected_charging', 'chrgr_sts_connected_no_chrg']

    def get_battery_level(self):
        return self.battery_level

    def get_current_schedules(self):
        request = {
            "operationName": "GetChargingSchedule",
            "variables": {
                "vehicleId": self.vehicle_id
            },
            "query": "query GetChargingSchedule($vehicleId: String!) { getVehicle(id: $vehicleId) { chargingSchedules { startTime duration location { latitude longitude } amperage enabled weekDays } } }"
        }
        headers = {
            'a-sess': self.app_session_token,
            'u-sess': self.user_session_token,
            'csrf-token': self.csrf_token,
            'apollographql-client-name': 'com.rivian.android.consumer'
        }
        response = requests.post(self.GATEWAY_URL, headers=headers, json=request)

        if response.status_code != 200:
            logger.error('Failed to make GraphQL request: {}'.format(response.text))
            return None

        data = response.json()
        return data['data']['getVehicle']['chargingSchedules']

    def get_current_schedule_amp(self):
        schedules = self.get_current_schedules()
        return schedules[0]['amperage']

    def set_schedule_custom(self, amps=AMPS_MAX):
        new_schedule = {
                "startTime": 0,
                "duration": 1440,
                "location": {
                },
                "amperage": self.AMPS_MAX,
                "enabled": True,
                "weekDays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            }

        if amps == 0:
            # Use time-specific schedule that does not overlap with the current time:
            # in the first half of the day use 18:00-19:00; second half — use 6:00-7:00
            current_hour = datetime.now().hour
            new_schedule["startTime"] = 18 * 60 if current_hour < 12 else 6 * 60
            new_schedule["duration"] = 60
        else:
            new_schedule["amperage"] = amps

        current_schedules = self.get_current_schedules()
        # copy the location from the existing schedule
        new_schedule["location"] = current_schedules[0]["location"]

        logger.info('Schedule to be set: {}'.format(new_schedule))

        # Don't make unnecessary updates
        if new_schedule == current_schedules[0]:
            logger.info('No change to the charging schedule. Not updating')
            return

        self.set_charging_schedule(new_schedule)

    def set_schedule_default(self):
        self.set_schedule_custom()

    def set_schedule_off(self):
        self.set_schedule_custom(amps=0)

    def set_schedule_amps(self, amps):
        self.set_schedule_custom(amps=amps)

    def set_charging_schedule(self, schedule):
        logger.info('Updating charging schedule: {}'.format(schedule))
        request = {
            "operationName": "SetChargingSchedule",
            "variables": {
                "vehicleId": self.vehicle_id,
                "chargingSchedules": [schedule]
            },
            "query": "mutation SetChargingSchedule($vehicleId: String!, $chargingSchedules: [InputChargingSchedule!]!) { setChargingSchedules(vehicleId: $vehicleId, chargingSchedules: $chargingSchedules) { success } }"
        }
        headers = {
            'a-sess': self.app_session_token,
            'u-sess': self.user_session_token,
            'csrf-token': self.csrf_token,
            'apollographql-client-name': 'com.rivian.android.consumer'
        }
        response = requests.post(self.GATEWAY_URL, headers=headers, json=request)

        if response.status_code == 200:
            logger.info('Charging schedule updated')
        else:
            logger.error('Failed to make GraphQL request: {}'.format(response.text))
