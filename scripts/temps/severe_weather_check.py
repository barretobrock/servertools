#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import hashlib
import pandas as pd
from kavalkilu import Log, LogArgParser, DarkSkyWeather, Paths
from kavalkilu.local_tools import slack_comm, notify_channel, user_me


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('severe_weather', log_dir='temps', log_lvl=LogArgParser().loglvl)

# Temp in C that serves as the floor of the warning
austin = '30.3428,-97.7582'
now = pd.datetime.now()
fpath = os.path.join(os.path.abspath(Paths().data_dir), 'severe_weather.json')

dark = DarkSkyWeather(austin)


def send_warning(row):
    """Sends warning to channel"""
    msg = '<@{}> - Incoming Alert!\n`{title}`\nFrom: `{time}` to `{expires}`' \
          '\n{description}\n\n{uri}'.format(user_me, **row.to_dict())
    slack_comm.send_message(notify_channel, msg)


# Read in the json file if there is one
if os.path.exists(fpath):
    old_alerts = pd.read_json(fpath)
else:
    old_alerts = pd.DataFrame()

alerts = dark.get_alerts()

if alerts is not None:
    for i, row in alerts.iterrows():
        if any([x in row['title'].lower() for x in ['child']]):
            # Skip non-weather related alerts
            continue
        # Hash the title and date
        hashed = hashlib.md5('{title}{time}'.format(**row).encode()).hexdigest()
        alerts.loc[i, 'hash'] = hashed
        # If the alert hash is not found in the dataframe, it's likely a new alert. Send a message to the channel
        if not old_alerts.empty:
            if hashed not in old_alerts['hash'].tolist():
                send_warning(row)
                old_alerts = old_alerts.append(alerts.iloc[i, :])
        else:
            # We've got an empty reference, so this is altogether a new alert
            send_warning(row)
            old_alerts = old_alerts.append(alerts.iloc[i, :])

if not old_alerts.empty:
    old_alerts = old_alerts.reset_index(drop=True)
    # Write old alerts to JSON
    old_alerts.to_json(fpath)

log.close()
