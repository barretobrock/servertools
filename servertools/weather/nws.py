from datetime import (
    datetime,
    timedelta,
)
from functools import reduce
import json
import pathlib
import re
from typing import (
    List,
    Union,
)

from dateutil import tz
import pandas as pd
import requests


class NWSAlertZone:
    """NWS zones for alerts"""
    ATX = ['TXC453', 'TXZ192']


class NWSAlert:
    """National Weather Service fun"""
    def __init__(self, target_zones: List[str]):
        self.zones = target_zones
        # This is where we store past alerts
        self.data_path = pathlib.Path().home().joinpath('data/severe_weather.csv')
        self.old_alerts = self.get_old_alerts()

    def get_old_alerts(self) -> pd.DataFrame:
        """Reads in past severe weather alerts"""
        if self.data_path.exists():
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
    def __init__(self, zone: str, timezone: str = 'US/Central'):
        """"""
        self.raw_data = self._get_raw_data(zone)
        self.tz = timezone

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
            if 'percent' in uom:
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
            return 'Nothing at all!'
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
