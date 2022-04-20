#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
import pandas as pd
from kavalkilu import LogWithInflux
from servertools import (
    SlackWeatherNotification,
    OpenWeather,
    OWMLocation,
    Plants,
    Plant
)

# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('plant_warn', log_dir='weather')

now = datetime.now()
# Instantiate plants
plants = Plants()
weather = OpenWeather(OWMLocation.ATX)
hours_df = weather.get_hourly_forecast()
# Convert date to datetime
hours_df['date'] = pd.to_datetime(hours_df['date'])

# Filter by column & get only the next 12 hours of forecasted weather
cols = ['date', 'temp-min']
hours_df = hours_df.loc[hours_df.date < (now + pd.Timedelta(hours=24)), cols]

# Get the lowest temp in the time range specified
lowest_temp = hours_df['temp-min'].min()
highest_min_plant_temp = plants.get_max_min_temp()
cold_plants_list = []
if highest_min_plant_temp >= lowest_temp:
    # Some plants' min temps are above the lowest temp in the time range
    cold_plants_list += plants.get_cold_plants(lowest_temp)

if len(cold_plants_list) > 0:
    # Capture the time range when the temp alert starts
    time_range = hours_df.loc[hours_df['temp-min'] < highest_min_plant_temp, 'date']
    swno = SlackWeatherNotification(parent_log=log)
    # Send alert
    swno.plant_alert(plants_list=cold_plants_list, hour_start=min(time_range), hour_end=max(time_range),
                     lowest_temp=lowest_temp)

log.close()
