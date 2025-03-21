# Solar Charging for Rivian

| WARNING: This script is provided as is, without any guarantees it will work for you. Use at your own risk.
| :---

This script automates charging a Rivian vehicle using excess solar energy produced by the Enphase PV system. It 
dynamically adjusts the vehicle's charging speed (in Amps) to align with the available surplus solar production.
Additionally, it can force charge to a certain level at night in case solar power alone is not enough for your daily
needs. 

<img src="https://github.com/ostap-korkuna/rivian-charging-automation/assets/44854323/e5781756-0f21-4e07-886c-8288c4bf8046" height="500"> &nbsp;
<img src="https://github.com/ostap-korkuna/rivian-charging-automation/assets/44854323/a0b3c539-b300-4fbf-b5b9-7a91d0d7f6ec" height="500"> &nbsp;
<img src="https://github.com/ostap-korkuna/rivian-charging-automation/assets/44854323/96393ac8-1590-437d-bd9d-c5851d172b60" height="500">


**Why not just use the Enphase IQ EV Charger and its native excess solar charging feature?**

I tried it, but was not impressed by how well it adjusts to solar production, mainly because its algorithm is very 
conservative, and it can only change the charging speed at 25% increments, while the charger inside the Rivian vehicle 
can make more precise adjustments between 8A and 48A with 2A steps. 

<img src="https://github.com/ostap-korkuna/rivian-charging-automation/assets/44854323/c6d2e0f3-d7a9-4c98-9203-a49ce4dae346" height="500">


## Requirements:
1) Rivian vehicle (tested on R1S)
2) Enphase solar system (solar gateway)
3) Raspberry Pi or similar always-on computer/server to run the automation script in Docker
4) (Optional) Hubitat home automation hub to monitor and switch charging automation modes from the mobile app

## How it works?
Every 10 minutes the script reads the solar production from Enphase solar gateway using the local API.
It checks how much solar is being exported to the grid, and calculates how many more Amps the EV charger should draw to 
consume all the excess solar. Formula: <Delta Amps> = <Solar export Watts> / 240
It then uses Rivian's Charging Schedule feature to set the desired amperage for charging (or disable changing) using 
Rivian web API (GraphQL).

At night, the script can either charge to a certain level (configurable) or not charge at all if you want to use solar
energy only.

The algorithm intentionally does not use the home battery to charge the EV during the day, and it will prioritize
charging the home battery if it's below 100%. This is because most home batteries are relatively small (compared to EV
batteries), so there would be little benefit, but it would complicate the algorithm quite a bit.   

### Automation Modes
The automation has three modes:
- OFF - Automation off
- DEFAULT - Use excess solar during the day and charge at full speed at night (to a certain limit)
- SOLAR_ONLY - only charge during the day using excess solar

### Step-by-step Algorithm
1. Check if the charger is plugged in. If not — disable charging and exit.
2. If in "default mode" (charge at night): Check if it's night time (configurable in `config.json`) AND the EV battery 
state of charge is below the set limit (default 50%) — if yes, set to maximum Amperage and exit.
3. Read production data from Enphase: Read net-consumption (import/export) 5 times, 10 seconds between readings. Take
the median as Grid Consumption.
4. Calculate the delta Amperage change: decrease by <Grid Consumption> / 240 rounded down to 2. Negative consumption —
increase Amperage; Positive — decrease it.
5. If -2 <= Amperage Change <= 2 — ignore small change to avoid flipping.
6. Current Amperage = Amerage from the schedule if Charging (check current session); if not charging == 0
7. New Amperage = Current Amperage + Amperage Change. If New Amperage > 48 => New Amperage = 48; If New Amperage < 8
=> New Amperage = 0.
8. If New Amperage != Current Amperage: update the charging schedule with New Amperage.
9. Wait 10 minutes before the next update.


## Setting Up

### 1. Check out the code

### 2. Create a config file and authenticate
Copy `config-example.json` as `config.json` and add your Rivian email/password, Enphase serial number, host IP
and authentication token.

See `Enphase-token.py` for how to get authentication token using your Enphase login and password.

Your `config.json` should look similar to this:

```json
{
    "rivian-user": "my-email@mail.com",
    "rivian-pass": "mysecretpass",
    "enphase-token": "asdkjhsdkjhakdjh.aksdsakd.skdlksajdlksajdlksajd",
    "enphase-gateway-sn": "202403011234",
    "enphase-gateway-host": "https://192.168.1.123",
    "night-time-start": 24,
    "night-time-end": 7
}
```

Rivian now requires 2-factor authentication. Run `python RivianSessionInitOTP.py` to initiate a Rivian API session.

### 3. [Optional] Create `hubitat-config.json`
If using Hubitat to control your automation, copy `hubitat-config-example.json` to `hubitat-config.json` and update with
your Hubitat configuration, otherwise skip this step (and comment out the corresponding code in
`ChargingAutomation.py`). 

See [Hubitat Setup](#hubitat-setup) for details.

### 4. Test the script
```shell
cd charging_automation
pip install --no-cache-dir -r requirements.txt
python main.py 
```
If the algorithm iteration runs successfully, proceed to the next step to build and run it in docker.

### 5. Build docker image
```shell
docker build -t charging_automation .
```

### 6. Start the service using docker compose
```shell
docker compose up -d
```

### 7. Set your EVSE to always-on
Disable any smart features of your EVSE, so it's always feeding power to the car when plugged in.


## Hubitat Setup

If you have a Hubitat home automation hub, then you can use it to control your charging automation modes (see
[Automation Modes](#automation-modes)).

Here is how my Hubitat dashboard looks like:

<img src="https://github.com/ostap-korkuna/rivian-charging-automation/assets/44854323/e5781756-0f21-4e07-886c-8288c4bf8046" height="500">

### 1. Create virtual devices
Create 3 virtual devices:
1. Virtual Switch to enable/disable automation
2. Virtual Dimmer to enable and configure nigh-time charging limit
3. Virtual Omni Sensor to publish the info from the script to display on the dashboard

### 2. Configure Maker API

See [Maker API docs](https://docs2.hubitat.com/en/apps/maker-api)

### 3. Update `hubitat-config.json`
Set the following values:
- **host**: Local IP address / URL to your Hubitat hub 
- **api-id**: 3-digit ID of you Maker API instance (it's part of every Maker API URL in Hubitat)
- **token**: access token generated by Maker API
- **automation-on-switch-id**: ID of a virtual switch for enabling/disabling automation
- **night-charge-switch-id**: ID of a virtual dimmer for enabling night charging and setting charging limit at night
- **info-device-id**: ID of a virtual omni sensor for publishing information to the dashboard

### 4. Complete the remaining steps from [Setting Up](#setting-up) section

### 5. Create a dashboard with your virtual switches
See example dashboard above.


## How to turn this OFF?
If you want to completely turn OFF and revert any changes made by this script, follow the steps below:

1. Stop the docker container using `docker stop` command
2. Go to your Rivian App and disable or modify the Charging Schedule set by this automation
3. Reconfigure your EVSE to the desired settings (i.e. disable "always-on")


# Credits
Thank you [Matthew1471](https://github.com/Matthew1471) for building and publishing [Enphase-API](https://github.com/Matthew1471/Enphase-API) 

Thank you [kaedenbrinkman](https://github.com/kaedenbrinkman) for publishing [Rivian API Documentation](https://github.com/kaedenbrinkman/rivian-api) 
