#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
from kavalkilu import Log, LogArgParser, DarkSkyWeather
from kavalkilu.local_tools import slack_comm, notify_channel, user_me


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('frost_warn', log_dir='temps', log_lvl=LogArgParser().loglvl)

# Temp in C that serves as the floor of the warning
austin = '30.3428,-97.7582'
now = pd.datetime.now()

dark = DarkSkyWeather(austin)
hours_df = dark.hourly_summary()
# Filter by column & get only the next 10 hours of forecasted temps
cols = ['time', 'temperature', 'apparentTemperature', 'dewPoint', 'windSpeed']
hours_df = hours_df.loc[hours_df.time < (now + pd.Timedelta(hours=12)), cols]

logic_dict = {
    'freeze': (hours_df.temperature < 0) & ((hours_df.dewPoint < -8) | (hours_df.windSpeed > 5)),
    'frost': (hours_df.temperature < 2) & ((hours_df.dewPoint < -6) | (hours_df.windSpeed >= 5)),
    'light frost': (hours_df.temperature < 2) & ((hours_df.dewPoint < -6) | (hours_df.windSpeed < 5)),
}

warning = None
for name, cond in logic_dict.items():
    if any(cond.tolist()):
        # We want the warnings to move from severe to relatively mild &
        # break on the first one that matches the condition
        warning = name
        break

if warning is not None:
    lowest_temp = hours_df.temperature.min()
    highest_wind = hours_df.windSpeed.max()
    msg = f'<@{user_me}> - {warning.title()} Warning: `{lowest_temp}C` `{highest_wind}m/s`'
    slack_comm.send_message(notify_channel, msg)

log.close()
