#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pandas as pd
from kavalkilu import Log
from servertools import NWSForecast, NWSForecastZone, SlackWeatherNotification


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('significant_change', log_dir='temps')

swno = SlackWeatherNotification()

now = datetime.now()
tomorrow = (now + timedelta(days=1))
weather = NWSForecast(NWSForecastZone.ATX)
hours_df = weather.get_hourly_forecast()
hours_df['date'] = pd.to_datetime(hours_df['date'])

# focus on just the following day's measurements
nextday = hours_df[hours_df['date'].dt.day == tomorrow.day].copy()
nextday['day'] = nextday['date'].dt.day
nextday['hour'] = nextday['date'].dt.hour
temp_dict = {}
metrics_to_collect = dict(zip(
    ['temp-avg', 'feels-temp-avg', 'precip-intensity', 'precip-prob'],
    ['temp', 'apptemp', 'precip_int', 'precip_prob'],
))
# Determine which hours are important to examine (e.g., for commuting / outside work)
important_hours = [0, 6, 12, 15, 18]
for hour in important_hours:
    hour_info = nextday[nextday['hour'] == hour]
    for metric, shortname in metrics_to_collect.items():
        temp_dict[f't{hour}_{shortname}'] = hour_info[metric].values[0]

temp_diff = temp_dict['t0_temp'] - temp_dict['t12_temp']
apptemp_diff = temp_dict['t0_apptemp'] - temp_dict['t12_apptemp']
if apptemp_diff >= 5:
    # Temp drops by greater than 5 degrees C. Issue warning.
    swno.sig_temp_change_alert(temp_diff, apptemp_diff, temp_dict)

# Send out daily report as well

report = []
for hour in important_hours:
    precip_multiplier = int(round(temp_dict[f't{hour}_precip_prob'] * 10 / 2)) - 1
    line = '{0:02d}:00\t{{t{0}_temp:.0f}}\t({{t{0}_apptemp:.1f}})\t{{t{0}_precip_prob:.1%}}\t' \
           '{{t{0}_precip_int:.2f}}'.format(hour).format(**temp_dict)
    if precip_multiplier > 0:
        line += f"\t{''.join([':rain-drops:'] * precip_multiplier)}"
    report.append(line)
swno.daily_weather_briefing(tomorrow, report)

log.close()
