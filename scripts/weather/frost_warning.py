#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

import pandas as pd
from pukr import get_logger

from servertools import (
    LOG_DIR,
    OpenWeather,
    OWMLocation,
    SlackWeatherNotification,
)

# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = get_logger('frost_warn', log_dir_path=LOG_DIR.joinpath('weather'))

now = datetime.now()
weather = OpenWeather(OWMLocation.ATX)
hours_df = weather.get_hourly_forecast()
# Convert date to datetime
hours_df['date'] = pd.to_datetime(hours_df['date'])

# Filter by column & get only the next 12 hours of forecasted weather
cols = ['date', 'temp-avg', 'temp-feels-like', 'dewpoint', 'wind-speed']
hours_df = hours_df.loc[hours_df.date < (now + pd.Timedelta(hours=24)), cols]

logic_dict = {
    'freeze': (hours_df['temp-avg'] < 0) & ((hours_df['dewpoint'] < -8) | (hours_df['wind-speed'] > 5)),
    'frost': (hours_df['temp-avg'] < 2) & ((hours_df['dewpoint'] < -6) | (hours_df['wind-speed'] >= 5)),
    'light frost': (hours_df['temp-avg'] < 2) & ((hours_df['dewpoint'] < -6) | (hours_df['wind-speed'] < 5)),
}

warning = None
for name, cond in logic_dict.items():
    hours_df[name] = cond
    if any(cond.tolist()):
        # We want the warnings to move from severe to relatively mild &
        # break on the first one that matches the condition
        warning = name
        break

if warning is not None:
    swno = SlackWeatherNotification(parent_log=log)
    lowest_temp = hours_df['temp-avg'].min()
    highest_wind = hours_df['wind-speed'].max()
    # Send alert
    swno.frost_alert(warning, lowest_temp, highest_wind)

log.close()
