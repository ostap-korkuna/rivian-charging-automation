import logging
import sys
import time
from ChargingAutomation import run_charging_automation

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        stream=sys.stdout
    )


def main():
    setup_logging()

    iteration_time = 10 * 60

    logger.info('Charging Automation Started: run every {} seconds'.format(iteration_time))

    while True:
        try:
            run_charging_automation()
        except Exception as e:
            logger.error("An error occurred:", e)
        logger.info('Sleeping for {} seconds...'.format(iteration_time))
        time.sleep(iteration_time)


if __name__ == '__main__':
    main()
