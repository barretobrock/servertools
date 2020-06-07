#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import requests
import re
from datetime import datetime, timedelta
from functools import reduce
from typing import List, Optional, Union
import pandas as pd
from meteocalc import feels_like, Temp, dew_point
from pyowm import OWM
from pyowm.weatherapi25.forecast import Forecast
from yr.libyr import Yr
from urllib.request import urlopen
from slacktools import BlockKitBuilder
from kavalkilu import Keys
from .slack_communicator import SlackComm


class SlackWeatherNotification:
    def __init__(self):
        self.bkb = BlockKitBuilder()
        self.sComm = SlackComm()

    @staticmethod
    def _format_severe_alert_text(alert_row: pd.Series) -> str:
        """Formats the row of alerts into a string"""
        alert_dict = alert_row.to_dict()
        alert_txt = "*`{event}`*({severity})\t\t`{start}` to `{end}`\n" \
                    "*{title}*\n{desc}".format(**alert_dict)
        return alert_txt

    def severe_weather_alert(self, alert_df: pd.DataFrame):
        """Formats a severe weather notification for Slack & sends it"""
        alert_list = []
        for idx, row in alert_df.iterrows():
            alert_list.append(self._format_severe_alert_text(row))

        alert_blocks = [
            self.bkb.make_context_section(f'{len(alert_list)} Incoming alert(s) <@{self.sComm.user_me}>!'),
            self.bkb.make_block_divider(),
            self.bkb.make_block_section(alert_list)
        ]

        self.sComm.st.send_message(self.sComm.notify_channel, '', blocks=alert_blocks)

    def frost_alert(self, warning: str, lowest_temp: float, highest_wind: float):
        """Handles routines for alerting to a frost warning"""
        blocks = [
            self.bkb.make_context_section(f'Frost/Freeze Alert <@{self.sComm.user_me}>!'),
            self.bkb.make_block_divider(),
            self.bkb.make_block_section(f'{warning.title()} Warning: *`{lowest_temp}`*C *`{highest_wind}`*m/s')
        ]
        self.sComm.st.send_message(self.sComm.notify_channel, '', blocks=blocks)



class NWSAlertZone:
    """NWS zones for alerts"""
    ATX = ['TXC453', 'TXZ192']


class NWSAlert:
    """National Weather Service fun"""
    def __init__(self, target_zones: List[str]):
        self.zones = target_zones
        # This is where we store past alerts
        self.data_path = os.path.join(os.path.expanduser('~'), *['data', 'severe_weather.csv'])
        self.old_alerts = self.get_old_alerts()

    def get_old_alerts(self) -> pd.DataFrame:
        """Reads in past severe weather alerts"""
        if os.path.exists(self.data_path):
            return pd.read_csv(self.data_path, sep=';')
        else:
            return pd.DataFrame()

    @staticmethod
    def _build_alert_url(zone: str) -> str:
        """Builds a url to the NWS alert API"""
        return f'https://api.weather.gov/alerts/active/zone/{zone}'

    def _get_raw_alert(self, zone: str) -> List[dict]:
        """Gets the raw response from the API call"""
        alert_url = self._build_alert_url(zone)
        resp = requests.get(alert_url)
        if resp.status_code != 200:
            raise ConnectionError('Unable to connect to NWS API')
        data = json.loads(resp.text)
        raw_alerts = data['features']
        return raw_alerts

    @staticmethod
    def _get_and_clean_description(properties: dict) -> str:
        """Cleans the raw alert description (which often has a lot of repetitive info"""
        desc = properties['description'].split('*')
        if len(desc) > 3:
            desc = desc[3]
        else:
            desc = desc[-1]

        return desc.replace('\n', ' ').strip()

    def _process_alert(self, alert: dict) -> pd.DataFrame:
        """Returns a cleaned alert"""
        properties = alert['properties']
        # Get alert id
        aid = properties['id']
        # Clean the description
        desc = self._get_and_clean_description(properties)
        return pd.DataFrame({
            'aid': aid,
            'start': pd.to_datetime(properties['effective']).strftime('%F %T'),
            'end': pd.to_datetime(properties['expires']).strftime('%F %T'),
            'severity': properties['severity'],
            'event': properties['event'],
            'title': properties['headline'],
            'desc': desc
        }, index=[0])

    def process_alerts(self) -> pd.DataFrame:
        """Batch cleans active alerts and checks them against old alerts"""
        # Begin collecting alerts
        active_alerts_df = pd.DataFrame()
        for zone in self.zones:
            alert_list = self._get_raw_alert(zone)
            for alert in alert_list:
                active_alerts_df.append(self._process_alert(alert))

        if active_alerts_df.empty:
            # Exit out before processing, since no active alerts
            return active_alerts_df

        # Check to see if any alert ids have already been entered
        #   into our old_alerts dataframe
        if not self.old_alerts.empty:
            active_alerts_df = active_alerts_df[~active_alerts_df['aid'].isin(self.old_alerts['aid'])]

        return active_alerts_df

    def save_alerts(self, alerts_df: pd.DataFrame):
        """Combines active alerts with old alerts & saves to CSV"""
        alerts = pd.concat(self.old_alerts, alerts_df).drop_duplicates()
        alerts.to_csv(self.data_path, sep=';')


class NWSForecastZone:
    """To find:
         - Get lat/long
         - apply here: https://api.weather.gov/points/30.346,-97.7707
         - under 'properties' -> 'forecastGridData'
    """
    ATX = 'EWX/154,93'


class NWSForecast:
    def __init__(self, zone: str):
        """"""
        self.raw_data = self._get_raw_data(zone)

    @staticmethod
    def _build_forecast_url(zone: str) -> str:
        """Builds a url to the NWS alert API"""
        return f'https://api.weather.gov/gridpoints/{zone}'

    def _get_raw_data(self, zone: str) -> dict:
        """Gets the raw response from the API call"""
        data_url = self._build_forecast_url(zone)
        resp = requests.get(data_url)
        if resp.status_code != 200:
            raise ConnectionError('Unable to connect to NWS API')
        resp_dict = json.loads(resp.text)
        raw_data = resp_dict['properties']
        return raw_data

    @staticmethod
    def _process_time(raw_str: str, as_dt=False) -> Union[List[str], List[datetime]]:
        """Processes NWS timestamp (2020-06-06T21:00:00+00:00/PT5H) into a list of datetime strings"""
        ts_str = re.search(r'[\d+\-]+T[\d:]+(?=\+)', raw_str).group()

        span_raw = re.search(r'(?<=/PT)\d+(?=H)', raw_str)
        if span_raw is None:
            # Day was also included
            span_raw = re.search(r'(?<=/P)[\w\d+]+(?=H)', raw_str)
            span = span_raw.group().split('DT')
            span = int(span[0]) * 24 + int(span[1])
        else:
            span = int(span_raw.group())

        ts_start = datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S')
        ts_end = (ts_start + timedelta(hours=span))
        dt_rng = pd.date_range(ts_start, ts_end, freq='1H', closed='left')
        if as_dt:
            return dt_rng.tolist()
        else:
            return dt_rng.strftime('%F %T').tolist()

    @staticmethod
    def _fahr_to_celsius(x: Union[float, int]):
        """Converts Fahrenheit to Celsius"""
        return (x - 32) * (5 / 9)

    def _process_data(self, data_type: str) -> pd.DataFrame:
        """Collects and processes temps from F to C"""
        raw_data_list = self.raw_data[data_type]['values']
        processed_data = []
        for raw_data in raw_data_list:
            dates = self._process_time(raw_data['validTime'])
            val = raw_data['value']
            processed_data += [{'date': x, data_type: val} for x in dates]
        data_df = pd.DataFrame(processed_data)
        # if any([x in data_type.lower() for x in ['temp', 'dew']]):
        #     # Convert temp data from F to C
        #     data_df[data_type] = data_df[data_type].apply(lambda x: self._fahr_to_celsius(x))
        return data_df

    def get_hourly_forecast(self) -> pd.DataFrame:
        """Processes raw forecast data into a dataframe"""
        df_list = []
        for data_type in ['temperature', 'dewpoint', 'relativeHumidity', 'apparentTemperature', 'skyCover', 'windSpeed']:
            df_list.append(self._process_data(data_type))

        # Combine the dataframes
        forecast_df = reduce(lambda left, right: pd.merge(left, right, on=['date'], how='outer'), df_list)
        return forecast_df

    def _build_summary(self, conditions: dict) -> str:
        """Takes in a dictionary of conditions and outputs a string"""
        coverage = conditions['coverage']
        weather = conditions['weather']
        intensity = conditions['intensity']

        if all([x is None for x in [coverage, weather, intensity]]):
            return f'Nothing at all!'
        else:
            coverage = coverage if coverage is not None else ''
            weather = weather if weather is not None else ''
            intensity = f'{intensity} ' if intensity is not None else ''
            return f'{coverage} {intensity}{weather}'.capitalize().replace('_', ' ')

    def get_summary(self, next_x_hrs: int) -> List[str]:
        """Gets a text summary for the next x hours"""
        raw_summary_list = self.raw_data['weather']['values']
        next_x_hrs_dt = (datetime.now() + timedelta(hours=next_x_hrs))\
            .replace(minute=0, second=0, microsecond=0)
        processed_summaries = []
        # Breaks the loop early if/when we hit the next_x_hrs limit
        break_on_this_iteration = False
        for raw_summary in raw_summary_list:
            dates = self._process_time(raw_summary['validTime'], as_dt=True)
            if next_x_hrs_dt in dates:
                dates = dates[:dates.index(next_x_hrs_dt)]
                break_on_this_iteration = True
            raw_conditions_list = raw_summary['value']
            summary_list = []
            for summary in raw_conditions_list:
                summary_list.append(self._build_summary(summary))
            # Remove duplicates
            summary_list = list(set(summary_list))
            if len(dates) == 1:
                processed_summary = f'At {dates[0].strftime("%H:00")}: {" and ".join(summary_list)}'
            else:
                processed_summary = f'From {dates[0].strftime("%H:00")} to {dates[-1].strftime("%H:00")}: ' \
                                    f'{" and ".join(summary_list)}'
            processed_summaries.append(processed_summary)
            if break_on_this_iteration:
                break
        return processed_summaries


class OWMLocation:
    """Locations for OWM"""
    ATX = 'Austin,US'
    TLL = 'Tallinn,EE'
    RKV = 'Rakvere,EE'


class OpenWeather:
    def __init__(self, location: str, tz: str = 'US/Central'):
        sk = Keys()
        self.api_key = sk.get_key('openweather_api')
        self.owm = OWM(self.api_key)
        self.location = location
        self.tz = tz

    def three_hour_summary(self) -> pd.DataFrame:
        """3h summary for the next 5 days"""
        data = self.owm.three_hours_forecast(self.location).get_forecast()
        return self._process_3h_fc_data(data, self.tz)

    def daily_summary(self) -> pd.DataFrame:
        """daily forecast for the next 5 days"""
        data = self.owm.daily_forecast(self.location, limit=5).get_forecast()
        return self._process_daily_fc_data(data, self.tz)

    @staticmethod
    def _process_daily_fc_data(data: Union[Forecast], tz: str) -> pd.DataFrame:
        cleaned = []
        for pt in data:
            # Extract temperatures (day, min, max, night, eve, morn)
            temps = {f'{k}Temp': v for k, v in pt.get_temperature('celsius').items()}
            temps['avgTemp'] = round((temps['minTemp'] + temps['maxTemp']) / 2, 2)
            wind = pt.get_wind('meters_sec')['speed']
            hum = pt.get_humidity()
            # Apply 'feels like' temperature
            feels = {f'apparent{k.title()}': round(feels_like(Temp(v, 'c'), hum, wind).c, 2)
                     for k, v in temps.items()}
            dew_pt = pt.get_dewpoint() if pt.get_dewpoint() is not None else dew_point(temps['avgTemp'], hum).c
            pt_dict = {
                'date': pd.to_datetime(pt.get_reference_time('iso')).tz_convert(tz).strftime('%F'),
                'summary': pt.get_detailed_status(),
                'precipIntensity': pt.get_rain().get('3h', 0),
                'dewPoint': round(dew_pt, 2),
                'humidity': hum / 100,
                'pressure': pt.get_pressure()['press'],
                'windSpeed': wind,
                'windBearing': pt.get_wind('meters_sec')['deg'],
                'cloudCover': pt.get_clouds() / 100,
                'visibility': pt.get_visibility_distance()
            }
            pt_dict.update(temps)
            pt_dict.update(feels)
            cleaned.append(pt_dict)
        return pd.DataFrame(cleaned)

    @staticmethod
    def _process_3h_fc_data(data: Union[Forecast], tz: str) -> pd.DataFrame:
        """Process 3-hour forecast data"""
        cleaned = []
        for pt in data:
            # Extract temperatures (day, min, max, night, eve, morn)
            temps_dict = pt.get_temperature('celsius')
            temps = {
                'avgTemp': temps_dict['temp'],
                'minTemp': temps_dict['temp_min'],
                'maxTemp': temps_dict['temp_max']
            }
            wind = pt.get_wind('meters_sec')['speed']
            hum = pt.get_humidity()
            # Apply 'feels like' temperature
            feels = {f'apparent{k.title()}': round(feels_like(Temp(v, 'c'), hum, wind).c, 2)
                     for k, v in temps.items()}
            dew_pt = pt.get_dewpoint() if pt.get_dewpoint() is not None else dew_point(temps['avgTemp'], hum).c
            pt_dict = {
                'date': pd.to_datetime(pt.get_reference_time('iso')).tz_convert(tz).strftime('%F'),
                'summary': pt.get_detailed_status(),
                'precipIntensity': pt.get_rain().get('3h', 0),
                'dewPoint': round(dew_pt, 2),
                'humidity': hum / 100,
                'pressure': pt.get_pressure()['press'],
                'windSpeed': wind,
                'windBearing': pt.get_wind('meters_sec')['deg'],
                'cloudCover': pt.get_clouds() / 100,
                'visibility': pt.get_visibility_distance()
            }
            pt_dict.update(temps)
            pt_dict.update(feels)
            cleaned.append(pt_dict)
        return pd.DataFrame(cleaned)


class YRNOLocation:
    """Locations for YRNO"""
    ATX = 'USA/Texas/Austin'
    TLL = 'Estonia/Harjumaa/Tallinn'
    RKV = 'Estonia/Lääne-Virumaa/Rakvere'


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
