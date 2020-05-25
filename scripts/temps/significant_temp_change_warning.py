#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
from kavalkilu import Log, LogArgParser, DarkSkyWeather
from kavalkilu.local_tools import slack_comm, notify_channel, user_me


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('significant_change', log_dir='temps', log_lvl=LogArgParser().loglvl)

# Temp in C that serves as the floor of the warning
austin = '30.3428,-97.7582'
now = pd.datetime.now()

dark = DarkSkyWeather(austin)


def send_warning(warn_msg):
    """Sends warning to channel"""
    msg = f'<@{user_me}> - {warn_msg}'
    slack_comm.send_message(notify_channel, msg)


next48 = dark.hourly_summary()
# Grab just temp and time columns
next48 = next48[['time', 'temperature', 'apparentTemperature', 'precipIntensity', 'precipProbability']]
# focus on just the following day's measurements
tomorrow = pd.Timedelta('1 days') + pd.datetime.now()
nextday = next48[next48['time'].dt.day == tomorrow.day].copy()

nextday['day'] = nextday['time'].dt.day
nextday['hour'] = nextday['time'].dt.hour
temp_dict = {}
metrics_to_collect = dict(zip(
    ['temperature', 'apparentTemperature', 'precipIntensity', 'precipProbability'],
    ['temp', 'apptemp', 'precip_int', 'precip_prob'],
))
hours = [0, 6, 12, 15, 18]
for hour in hours:
    hour_info = nextday[nextday['hour'] == hour]
    for metric, shortname in metrics_to_collect.items():
        temp_dict[f't{hour}_{shortname}'] = hour_info[metric].values[0]

temp_diff = temp_dict['t0_temp'] - temp_dict['t12_temp']
apptemp_diff = temp_dict['t0_apptemp'] - temp_dict['t12_apptemp']
if apptemp_diff >= 5:
    # Temp drops by greater than 5 degrees C. Issue warning.
    warn = 'Temp higher at midnight `{t0_temp:.2f} ({t0_apptemp:.2f})` ' \
           'than midday `{t12_temp:.2f} ({t12_apptemp:.2f})` ' \
           'diff: `{:.1f} ({:.1f})`'.format(temp_diff, apptemp_diff, **temp_dict)
    send_warning(warn)

# Send out daily report as well

report = f"""
*Weather Report for {tomorrow:%A, %d %B}*
"""
for hour in hours:
    precip_multiplier = int(round(temp_dict[f't{hour}_precip_prob'] * 10 / 2)) - 1
    line = '{0:02d}:00\t{{t{0}_temp:.0f}}\t({{t{0}_apptemp:.1f}})\t{{t{0}_precip_prob:.1%}}\t' \
           '{{t{0}_precip_int:.2f}}'.format(hour).format(**temp_dict)
    if precip_multiplier > 0:
        line += f"\t{''.join([':rain-drops:'] * precip_multiplier)}"
    report += f'{line}\n'

slack_comm.send_message(notify_channel, report)

log.close()
