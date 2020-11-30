#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pandas as pd
from kavalkilu import LogWithInflux
from servertools import NWSForecast, NWSForecastZone, SlackWeatherNotification


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('significant_change', log_dir='weather')

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
    temp_dict[hour] = {
        f'{shortname}': hour_info[metric].values[0] for metric, shortname in metrics_to_collect.items()
    }

temp_diff = temp_dict[0]['temp'] - temp_dict[12]['temp']
apptemp_diff = temp_dict[0]['apptemp'] - temp_dict[12]['apptemp']
if apptemp_diff >= 5:
    # Temp drops by greater than 5 degrees C. Issue warning.
    swno.sig_temp_change_alert(temp_diff, apptemp_diff, temp_dict)

# Send out daily report as well

report = ['hour\tt\tft\tr-prob\tr-int']
for h in important_hours:
    precip_multiplier = int(round(temp_dict[h]['precip_prob'] * 10 / 2) - 1)
    line = f'{h:02d}:00\t{temp_dict[h]["temp"]:.0f}\t({temp_dict[h]["apptemp"]:.1f})\t' \
           f'{temp_dict[h]["precip_prob"]:.1%}\t{temp_dict[h]["precip_int"]:.2f}'
    if precip_multiplier > 0:
        line += f"\t{''.join([':droplet:'] * precip_multiplier)}"
    report.append(line)
swno.daily_weather_briefing(tomorrow, report)

log.close()
