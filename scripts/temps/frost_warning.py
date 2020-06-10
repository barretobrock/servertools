#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import pandas as pd
from kavalkilu import Log
from servertools import SlackWeatherNotification, NWSForecast, NWSForecastZone

# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('frost_warn', log_dir='temps')

now = datetime.now()
weather = NWSForecast(NWSForecastZone.ATX)
hours_df = weather.get_hourly_forecast()
hours_df['date'] = pd.to_datetime(hours_df['date'])

# Filter by column & get only the next 12 hours of forecasted temps
cols = ['date', 'temperature', 'apparentTemperature', 'dewpoint', 'windSpeed']
hours_df = hours_df.loc[hours_df.date < (now + pd.Timedelta(hours=12)), cols]

logic_dict = {
    'freeze': (hours_df.temperature < 0) & ((hours_df.dewpoint < -8) | (hours_df.windSpeed > 5)),
    'frost': (hours_df.temperature < 2) & ((hours_df.dewpoint < -6) | (hours_df.windSpeed >= 5)),
    'light frost': (hours_df.temperature < 2) & ((hours_df.dewpoint < -6) | (hours_df.windSpeed < 5)),
}

warning = None
for name, cond in logic_dict.items():
    if any(cond.tolist()):
        # We want the warnings to move from severe to relatively mild &
        # break on the first one that matches the condition
        warning = name
        break

if warning is not None:
    swno = SlackWeatherNotification()
    lowest_temp = hours_df.temperature.min()
    highest_wind = hours_df.windSpeed.max()
    # Send alert
    swno.frost_alert(warning, lowest_temp, highest_wind)

log.close()
