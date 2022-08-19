#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from kavalkilu import LogWithInflux

from servertools import (
    NWSAlert,
    NWSAlertZone,
    SlackWeatherNotification,
)

# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('severe_weather', log_dir='weather')

nwa = NWSAlert(NWSAlertZone.ATX)
slacknotify = SlackWeatherNotification(parent_log=log)

alerts = nwa.process_alerts()
if not alerts.empty:
    slacknotify.severe_weather_alert(alerts)
    # Save new alerts
    nwa.save_alerts(alerts)

log.close()
