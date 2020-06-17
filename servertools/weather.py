#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import json
import requests
import pandas as pd
from typing import List, Optional, Union, Any
from datetime import datetime, timedelta
from dateutil import tz
from functools import reduce
from meteocalc import feels_like, Temp, dew_point
from pyowm import OWM
from pyowm.weatherapi25.weather import Weather
from pyowm.weatherapi25.forecast import Forecast
from yr.libyr import Yr
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

    def _notify_channel(self, alert_blocks: List[dict]):
        """Wrapper function to send alert to notification channel"""
        self.sComm.st.send_message(self.sComm.notify_channel, '', alert_blocks)

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
        self._notify_channel(alert_blocks)

    def frost_alert(self, warning: str, lowest_temp: float, highest_wind: float):
        """Handles routines for alerting to a frost warning"""
        blocks = [
            self.bkb.make_context_section(f'Frost/Freeze Alert <@{self.sComm.user_me}>!'),
            self.bkb.make_block_divider(),
            self.bkb.make_block_section(f'{warning.title()} Warning: *`{lowest_temp}`*C *`{highest_wind}`*m/s')
        ]
        self._notify_channel(blocks)

    def sig_temp_change_alert(self, temp_diff: float, apptemp_diff: float, temp_dict: dict):
        """Handles routines for alerting a singificant change in temperature"""
        msg_text = 'Temp higher at midnight `{t0_temp:.2f} ({t0_apptemp:.2f})` ' \
                   'than midday `{t12_temp:.2f} ({t12_apptemp:.2f})` '\
                   'diff: `{:.1f} ({:.1f})`'.format(temp_diff, apptemp_diff, **temp_dict)
        blocks = [
            self.bkb.make_context_section(f'Significant Temp Change Alert <@{self.sComm.user_me}>!'),
            self.bkb.make_block_divider(),
            self.bkb.make_block_section(msg_text)
        ]
        self._notify_channel(blocks)

    def daily_weather_briefing(self, tomorrow: datetime, report: List[str]):
        """Presents a daily weather report for the work week"""
        blocks = [
            self.bkb.make_context_section(f'*Weather Report for {tomorrow:%A, %d %B}*'),
            self.bkb.make_block_divider(),
            self.bkb.make_block_section(report)
        ]
        self._notify_channel(blocks)


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
    def __init__(self, zone: str, tz: str = 'US/Central'):
        """"""
        self.raw_data = self._get_raw_data(zone)
        self.tz = tz

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

    def _process_time(self, raw_str: str, as_dt=False) -> Union[List[str], List[datetime]]:
        """Processes NWS timestamp (2020-06-06T21:00:00+00:00/PT5H) into a list of datetime strings"""
        # Capture starting timestamp
        ts_str = re.search(r'[\d+\-]+T[\d:]+(?=\+)', raw_str).group()
        # Duration area
        # Capture day only
        day_dur_match = re.search(r'(?<=P)\d+(?=D)', raw_str)
        day_dur = 0 if day_dur_match is None else int(day_dur_match.group())
        # Capture hour only
        hour_dur_match = re.search(r'(?<=T)\d+(?=H)', raw_str)
        hour_dur = 0 if hour_dur_match is None else int(hour_dur_match.group())

        # Add up the hours
        span = (24 * day_dur) + hour_dur

        # Convert timestamp to UTC datetime obj
        utc = tz.gettz('UTC')
        local = tz.gettz(self.tz)
        utc_dt = datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=utc)
        local_dt = utc_dt.astimezone(local)

        # Set in local time
        ts_start = local_dt
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
        uom = self.raw_data[data_type]['uom']
        processed_data = []
        for raw_data in raw_data_list:
            dates = self._process_time(raw_data['validTime'])
            val = raw_data['value']
            if uom == 'unit:percent':
                val = val / 100 if val > 0 else 0
            processed_data += [{'date': x, data_type: val} for x in dates]
        data_df = pd.DataFrame(processed_data)
        return data_df

    def get_hourly_forecast(self) -> pd.DataFrame:
        """Processes raw forecast data into a dataframe"""
        # Original: new
        data_cols = {
            'temperature': 'temp-avg',
            'dewpoint': 'dewpoint',
            'relativeHumidity': 'relative-humidity',
            'apparentTemperature': 'feels-temp-avg',
            'skyCover': 'cloud-cover',
            'windSpeed': 'wind-speed',
            'probabilityOfPrecipitation': 'precip-prob',
            'quantitativePrecipitation': 'precip-intensity'
        }

        df_list = []
        for original, new_col in data_cols.items():
            df_list.append(self._process_data(original).rename(columns={original: new_col}))

        # Combine the dataframes
        forecast_df = reduce(lambda left, right: pd.merge(left, right, on=['date'], how='outer'), df_list)

        return forecast_df

    @staticmethod
    def _build_summary(conditions: dict) -> str:
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

    def current_weather(self) -> pd.DataFrame:
        """Gets current weather for location"""
        cur = self.owm.weather_at_place(self.location).get_weather()
        cur_df = self._process_current_weather_data(cur)
        return cur_df

    def three_hour_summary(self) -> pd.DataFrame:
        """3h summary for the next 5 days"""
        data = self.owm.three_hours_forecast(self.location).get_forecast()
        return self._process_3h_fc_data(data)

    def daily_summary(self) -> pd.DataFrame:
        """daily forecast for the next 5 days"""
        data = self.owm.daily_forecast(self.location, limit=5).get_forecast()
        return self._process_daily_fc_data(data)

    def _extract_common_weather_data(self, datapoint: Any, temperatures: dict) -> dict:
        """Extracts common (unchanging from hourly/daily methods) weather data
        from a given data point"""
        wind = datapoint.get_wind('meters_sec')['speed']
        hum = datapoint.get_humidity()
        # Apply 'feels like' temperature
        feels = {f'feels-{k.lower()}': round(feels_like(Temp(v, 'c'), hum, wind).c, 2)
                 for k, v in temperatures.items()}
        dew_pt = datapoint.get_dewpoint() if datapoint.get_dewpoint() is not None \
            else dew_point(temperatures['temp-avg'], hum).c
        pt_dict = {
            'date': pd.to_datetime(datapoint.get_reference_time('iso')).tz_convert(self.tz).strftime('%F'),
            'summary': datapoint.get_detailed_status(),
            'precip-intensity': datapoint.get_rain().get('3h', 0),
            'dewpoint': round(dew_pt, 2),
            'humidity': hum / 100,
            'pressure': datapoint.get_pressure()['press'],
            'wind-speed': wind,
            'wind-bearing': datapoint.get_wind('meters_sec')['deg'],
            'cloud-cover': datapoint.get_clouds() / 100,
            'visibility': datapoint.get_visibility_distance()
        }
        pt_dict.update(temperatures)
        pt_dict.update(feels)
        return pt_dict

    def _process_daily_fc_data(self, data: Forecast) -> pd.DataFrame:
        """Process daily forecast data"""
        cleaned = []
        for pt in data:
            # Extract temperatures (day, min, max, night, eve, morn)
            temps = {f'temp-{k}': v for k, v in pt.get_temperature('celsius').items()}
            temps['temp-avg'] = round((temps['temp-min'] + temps['temp-max']) / 2, 2)
            cleaned.append(self._extract_common_weather_data(pt, temps))
        return pd.DataFrame(cleaned)

    def _process_3h_fc_data(self, data: Forecast) -> pd.DataFrame:
        """Process 3-hour forecast data"""
        cleaned = []
        for pt in data:
            # Extract temperatures (day, min, max, night, eve, morn)
            temps_dict = pt.get_temperature('celsius')
            temps = {
                'temp-avg': temps_dict['temp'],
                'temp-min': temps_dict['temp_min'],
                'temp-max': temps_dict['temp_max']
            }
            cleaned.append(self._extract_common_weather_data(pt, temps))
        return pd.DataFrame(cleaned)

    def _process_current_weather_data(self, data: Weather) -> pd.DataFrame:
        """Process current weather data"""
        cleaned = []
        temps_dict = data.get_temperature('celsius')
        temps = {
            'temp-avg': temps_dict['temp'],
            'temp-min': temps_dict['temp_min'],
            'temp-max': temps_dict['temp_max']
        }
        cleaned.append(self._extract_common_weather_data(data, temps))
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
            'precip-intensity': float(data['precipitation']['@value']),
            'wind-bearing': float(data['windDirection']['@deg']),
            'wind-speed': float(data['windSpeed']['@mps']),
            'wind-summary': data['windSpeed']['@name'],
            'temp-avg': float(data['temperature']['@value']),
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
