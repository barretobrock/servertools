#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from typing import List, Optional, Union
import pandas as pd
from meteocalc import feels_like, Temp, dew_point
from pyowm import OWM
from pyowm.weatherapi25.forecast import Forecast
from yr.libyr import Yr
from urllib.request import urlopen
from .keys import ServerKeys


# Locations for OWM
OWM_ATX = 'Austin,US'
OWM_TLL = 'Tallinn,EE'
OWM_RKV = 'Rakvere,EE'

# Some common locations for YrNo
YRNO_LOC_ATX = 'USA/Texas/Austin'
YRNO_LOC_TLL = 'Estonia/Harjumaa/Tallinn'
YRNO_LOC_RKV = 'Estonia/Lääne-Virumaa/Rakvere'

# NWS zones for alerts
NWS_ZONES_ATX = ['TXC453', 'TXZ192']


class OpenWeather:
    def __init__(self, location: str, tz: str = 'US/Central'):
        sk = ServerKeys()
        self.api_key = sk.get_key('openweather_api')
        self.owm = OWM(self.api_key)
        self.location = location
        self.tz = tz

    def three_hour_summary(self) -> pd.DataFrame:
        """3h summary for the next 5 days"""
        data = self.owm.three_hours_forecast(self.location).get_forecast()
        return self._process_data(data, self.tz)

    def daily_summary(self) -> pd.DataFrame:
        """daily forecast for the next 5 days"""
        data = self.owm.daily_forecast(self.location, limit=5).get_forecast()
        return self._process_data(data, self.tz)

    @staticmethod
    def _process_data(data: Union[Forecast], tz: str) -> pd.DataFrame:
        cleaned = []
        for pt in data:
            temp = pt.get_temperature('celsius')['temp']
            wind = pt.get_wind('meters_sec')['speed']
            hum = pt.get_humidity()
            feels = feels_like(Temp(temp, 'c'), hum, wind).c
            dew_pt = pt.get_dewpoint() if pt.get_dewpoint() is not None else dew_point(temp, hum).c
            pt_dict = {
                'time': pd.to_datetime(pt.get_reference_time('iso')).tz_convert(tz),
                'summary': pt.get_detailed_status(),
                'precipIntensity': pt.get_rain()['3h'],
                'temperature': temp,
                'apparentTemperature': feels,
                'dewPoint': dew_pt,
                'humidity': hum / 100,
                'pressure': pt.get_pressure()['press'],
                'windSpeed': wind,
                'windBearing': pt.get_wind('meters_sec')['deg'],
                'cloudCover': pt.get_clouds() / 100,
                'visibility': pt.get_visibility_distance()
            }
            cleaned.append(pt_dict)
        return pd.DataFrame(cleaned)


class YrNoWeather:
    """Pulls weather data using Yr.no weather API"""
    def __init__(self, location: str, tz: str = 'US/Central'):
        """
        Args:
            location(str): location name `country/region/city`
            tz(str):  time zone to record time
        """
        self.location = location
        self.tz = tz

    @staticmethod
    def _process_data(data: dict) -> dict:
        """Process the raw data from YrNo API"""
        return {
            'from': pd.to_datetime(data['@from']),
            'to': pd.to_datetime(data['@to']),
            'summary': data['symbol']['@name'],
            'precipIntensity': float(data['precipitation']['@value']),
            'windBearing': float(data['windDirection']['@deg']),
            'windSpeed': float(data['windSpeed']['@mps']),
            'windSummary': data['windSpeed']['@name'],
            'temperature': float(data['temperature']['@value']),
            'pressure': float(data['pressure']['@value'])
        }

    def current_summary(self) -> pd.DataFrame:
        """Collect the current weather data for the location"""
        data = Yr(location_name=self.location).now()
        cleaned = pd.DataFrame(self._process_data(data), index=[1])
        return cleaned

    def hourly_summary(self) -> pd.DataFrame:
        """Creates a 48 hour forecast summary"""
        data = Yr(location_name=self.location, forecast_link='forecast_hour_by_hour')
        return pd.DataFrame([self._process_data(x) for x in data.forecast()])

    def daily_summary(self) -> pd.DataFrame:
        """Creates a 7-day forecast summary"""
        data = Yr(location_name=self.location)
        df = pd.DataFrame([self._process_data(x) for x in data.forecast()])
        # We'll need to group by day and have high/low calculated for each metric
        keep_cols = ['from', 'precipIntensity', 'windSpeed', 'temperature', 'pressure']
        df = df[keep_cols].groupby(pd.Grouper(key='from', freq='D')).agg(
            {x: ['min', 'max'] for x in keep_cols[1:]}
        )
        # Flatten the columns for the dataframe, but keep everything preserved from each level
        df.columns = ['_'.join(col).strip() for col in df.columns.values]
        return df


class DarkSkyWeather:
    """
    Use Dark Sky API to get weather forecast
    Args for __init__:
        latlong: str, format: "latitude,longitude"
    """
    def __init__(self, latlong='59.4049,24.6768', tz='US/Central'):
        self.latlong = latlong
        self.tz = tz
        self.url_prefix = 'https://api.darksky.net/forecast'
        k = ServerKeys()
        self.DARK_SKY_API = k.get_key('darksky_api')
        self.DARK_SKY_URL = "{}/{}/{}?units=si&exclude=flags".format(self.url_prefix, self.DARK_SKY_API, self.latlong)
        self.data = self._get_data()

    def _get_data(self):
        """Returns weather data on given location"""
        # get weather forecast from dark sky api
        darksky = urlopen(self.DARK_SKY_URL).read().decode('utf-8')
        data = json.loads(darksky)
        return data

    def _format_tables(self, data):
        """Takes in a grouping of data and returns as a pandas dataframe"""
        if isinstance(data, list):
            # Dealing with multiple rows of data
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Dealing with a single row of data
            df = pd.DataFrame(data, index=[0])

        # Convert any "time" column to locally-formatted datetime
        time_cols = [col for col in df.columns if any([x in col.lower() for x in ['time', 'expire']])]
        df = self._convert_time_cols(time_cols, df)

        return df

    def _convert_time_cols(self, cols, df):
        """Converts time columns from epoch to local time"""
        if len(cols) > 0:
            for time_col in cols:
                # Convert column to datetime
                dtt_col = pd.to_datetime(df[time_col], unit='s')
                # Convert datetime col to local timezone and remove tz
                dtt_col = dtt_col.dt.tz_localize('utc').dt.tz_convert(self.tz).dt.tz_localize(None)
                df[time_col] = dtt_col
        return df

    def current_summary(self):
        """Get current weather summary"""
        data = self.data['currently']
        df = self._format_tables(data)
        return df

    def hourly_summary(self):
        """Get 48 hour weather forecast"""
        data = self.data['hourly']['data']
        df = self._format_tables(data)
        return df

    def daily_summary(self):
        """Get 7-day weather forecast"""
        data = self.data['daily']['data']
        df = self._format_tables(data)
        return df

    def get_alerts(self):
        """Determines if there are any active weather alerts"""
        if 'alerts' not in self.data.keys():
            # No alerts
            return None
        alerts = self.data['alerts']
        df = self._format_tables(alerts)
        return df
