#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import (
    datetime,
    timedelta
)
import pandas as pd
from kavalkilu import LogWithInflux
from servertools import (
    YrNoWeather,
    YRNOLocation,
    SlackWeatherNotification
)
from servertools.plants import Plants


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('significant_change', log_dir='weather')

swno = SlackWeatherNotification(parent_log=log)
plants = Plants()

now = datetime.now()
tomorrow = (now + timedelta(hours=36))

# Get weather details
wx = YrNoWeather(location=YRNOLocation.ATX)
forecast_df = wx.hourly_summary()
forecast_df['date'] = pd.to_datetime(forecast_df['from'])
forecast_df = forecast_df[['date', 'temp-avg']]
# Filter on next 48 hours
forecast_df = forecast_df.loc[forecast_df['date'] <= tomorrow]
# Get lowest temp
lowest = forecast_df['temp-avg'].min()
# Extract plants that might be affected
affected_plants = plants.get_plants_below(lowest)

if len(affected_plants) > 0:
    # Get the highest low temp of the affected plants
    highest_lowtemp = max([x.temp_min for x in affected_plants])
    # Get the times in which the temps fall below highest_lowtemp
    lowtemps_df = forecast_df.loc[forecast_df['temp-avg'] <= highest_lowtemp]
    # TODO: Group consistent hours for display (e.g., 3pm - 8am)
    # TODO: Build message blocks for these that include plant names


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
