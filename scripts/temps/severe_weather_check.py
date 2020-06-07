#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from kavalkilu import Log
from servertools import NWSAlert, NWSAlertZone, SlackWeatherNotification


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('severe_weather', log_dir='temps')

nwa = NWSAlert(NWSAlertZone.ATX)
slacknotify = SlackWeatherNotification()

alerts = nwa.process_alerts()
if not alerts.empty:
    slacknotify.severe_weather_alert(alerts)
    # Save new alerts
    nwa.save_alerts(alerts)

log.close()
