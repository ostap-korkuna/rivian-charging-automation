import logging
import math
from datetime import datetime
from enum import Enum
from RivianAPI import RivianAPI
from EnphaseAPI import EnphaseAPI
from HubitatAPI import HubitatAPI

logger = logging.getLogger(__name__)


class AutomationMode(Enum):
    OFF = 0  # charging automation off
    DEFAULT = 1  # using excess solar during the day, charging at full speed at night (up to a limit)
    SOLAR_ONLY = 2  # only using excess solar, not charging at night


def is_night_time():
    current_hour = datetime.now().hour
    return current_hour < 7 or current_hour >= 24


def calculate_delta_amp(grid_consumption):
    # Amp = Watt / 240
    # round up to 2Amp — charger minimal step
    # If grid consumption is positive we want to round up and decrease more to avoid consuming at all.
    # If consumption is negative we also round up a negative number to make a smaller absolute increase in Amps.

    delta_amp = -math.ceil(grid_consumption / 240 / 2) * 2
    return delta_amp


def is_delta_amp_too_small(delta_amp):
    return -3 < delta_amp < 3


def get_automation_mode(hubitat):
    # If not using Hubitat, hardcode the automation mode
    if not hubitat:
        return AutomationMode.SOLAR_ONLY

    automation_on = hubitat.is_automation_on()
    night_charging = hubitat.is_night_charging_on()
    if not automation_on:
        return AutomationMode.OFF
    return AutomationMode.DEFAULT if night_charging else AutomationMode.SOLAR_ONLY


def get_night_charging_limit(hubitat):
    # If not using Hubitat, hardcode 50%
    if not hubitat:
        return 50

    limit = hubitat.get_night_charging_limit()
    return limit


def run_charging_automation():
    logger.info('Running charging automation cycle...')

    hubitat = HubitatAPI('hubitat-config.json')
    # If not using Hubitat replace with the line below
    # hubitat = None

    logger.info('Reading config from Hubitat...')
    mode = get_automation_mode(hubitat)

    logger.info('Automation mode: {}'.format(mode))

    # Check automation is ON
    if mode == AutomationMode.OFF:
        logger.info('Automation is OFF')
        return

    rivian = RivianAPI('credentials.json', 'rivian-session.json')
    enphase = EnphaseAPI('credentials.json')

    # Check if charger is plugged in
    if not rivian.is_charger_connected():
        logger.info('Charger not plugged in')
        rivian.set_schedule_off()
        if hubitat:
            hubitat.set_info_message('Charging: not plugged in', 0, 0)
        return

    # Check night time
    if is_night_time():
        if mode == AutomationMode.SOLAR_ONLY:
            logger.info('Mode == Solar-only: Disabling charging at night')
            rivian.set_schedule_off()
            if hubitat:
                hubitat.set_info_message('Charging: disabled (night off)', 0, 0)
        if mode == AutomationMode.DEFAULT:
            # In default mode, charge to a certain % at night
            charging_limit = get_night_charging_limit(hubitat)
            ev_battery_level = rivian.get_battery_level()
            if ev_battery_level < charging_limit:
                logger.info('Mode == Default: Charging to {}% at night (now at {}%)'.format(
                    charging_limit, round(ev_battery_level)))
                rivian.set_schedule_default()
                if hubitat:
                    hubitat.set_info_message('Charging: enabled (night)', RivianAPI.AMPS_MAX, 0)
            else:
                logger.info('Mode == Default: Charged to {}% at night (already at {}%)'.format(
                    charging_limit, round(ev_battery_level)))
                rivian.set_schedule_off()
                if hubitat:
                    hubitat.set_info_message('Charging: disabled (night full)', 0, 0)
        return

    # Read production data from Enphase
    grid_consumption = enphase.get_median_grid_consumption()
    delta_amp = calculate_delta_amp(grid_consumption)
    current_amp = rivian.get_current_schedule_amp() if rivian.is_charging() else 0
    logger.info('Grid consumption: {} ; Current Amp: {} ; Delta Amp: {}'.format(grid_consumption, current_amp, delta_amp))

    if is_delta_amp_too_small(delta_amp):
        # Ignore small changes to avoid flipping
        logger.info('Small or no change. Ignoring')
        # Always set the expected state
        rivian.set_schedule_amps(current_amp)
        if hubitat:
            hubitat.set_info_message(
                'Charging: disabled' if current_amp == 0 else 'Charging: enabled',
                current_amp,
                grid_consumption)
        return

    new_amp = current_amp + delta_amp
    if new_amp > RivianAPI.AMPS_MAX:
        new_amp = RivianAPI.AMPS_MAX
    if new_amp < RivianAPI.AMPS_MIN:
        new_amp = 0

    logger.info('Current Amp: {} ; New Amp: {}'.format(current_amp, new_amp))
    if new_amp == 0:
        rivian.set_schedule_off()
        if hubitat:
            hubitat.set_info_message('Charging: disabled', new_amp, grid_consumption)
    else:
        rivian.set_schedule_amps(new_amp)
        if hubitat:
            hubitat.set_info_message('Charging: enabled', new_amp, grid_consumption)

    logger.info('Automation cycle complete')
