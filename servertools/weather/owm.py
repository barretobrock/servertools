from typing import (
    Any,
    Union,
    Dict
)
from meteocalc import (
    feels_like,
    Temp,
    dew_point
)
import pandas as pd
from pyowm import OWM
from pyowm.weatherapi25.forecast import Forecast
from pyowm.weatherapi25.weather import Weather
from kavalkilu import Keys


class OWMLocation:
    """Locations for OWM"""
    ATX = 'Austin,US'
    TLL = 'Tallinn,EE'
    RKV = 'Rakvere,EE'


class OpenWeather:
    def __init__(self, location: str, timezone: str = 'US/Central'):
        sk = Keys()
        self.api_key = sk.get_key('openweather').get('token', '')
        self.owm = OWM(self.api_key)
        self.location = location
        self.tz = timezone

    def get_current_summary(self) -> pd.DataFrame:
        """Gets current weather for location"""
        cur = self.owm.weather_manager().weather_at_place(self.location).weather
        cur_df = self._process_current_weather_data(cur)
        return cur_df

    def get_three_hour_forecast(self) -> pd.DataFrame:
        """3h summary for the next 5 days"""
        data = self.owm.weather_manager().forecast_at_place(self.location, '3h').forecast
        # data = self.owm.three_hours_forecast(self.location).get_forecast()
        return self._process_3h_fc_data(data)

    def get_hourly_forecast(self) -> pd.DataFrame:
        """hourly summary (just three hours with gaps filled in) for the next 5 days"""
        data = self.owm.weather_manager().forecast_at_place(self.location, '3h').forecast
        # data = self.owm.three_hours_forecast(self.location).get_forecast()
        data = self._process_3h_fc_data(data)
        rng = pd.date_range(
            pd.to_datetime(data.iloc[0, 0]), pd.to_datetime(data.iloc[-1, 0]), freq='1H')
        time_df = pd.DataFrame({'date': [x.strftime('%F %T') for x in rng.tolist()]})
        data = time_df.merge(data, on='date', how='left').fillna(method='ffill')
        return data

    def get_daily_forecast(self) -> pd.DataFrame:
        """daily forecast for the next 5 days"""
        data = self.owm.weather_manager().forecast_at_place(self.location, 'daily').forecast
        # data = self.owm.daily_forecast(self.location, limit=5).get_forecast()
        return self._process_daily_fc_data(data)

    def _extract_common_weather_data(self, datapoint: Any, temperatures: dict) -> dict:
        """Extracts common (unchanging from hourly/daily methods) weather data
        from a given data point"""
        wind = datapoint.wind('meters_sec').get('speed')
        hum = datapoint.humidity
        # Apply 'feels like' temperature
        feels = {f'feels-{k.lower()}': round(feels_like(Temp(v, 'c'), hum, wind).c, 2)
                 for k, v in temperatures.items() if 'feels' not in k}
        dew_pt = datapoint.dewpoint if datapoint.dewpoint is not None \
            else dew_point(temperatures['temp-avg'], hum).c
        pt_dict = {
            'date': pd.to_datetime(datapoint.reference_time('iso')).tz_convert(self.tz).strftime('%F %T'),
            'summary': datapoint.detailed_status,
            'precip-intensity': datapoint.rain.get('3h', 0),
            'dewpoint': round(dew_pt, 2),
            'humidity': hum / 100,
            'pressure': datapoint.pressure.get('press'),
            'wind-speed': wind,
            'wind-bearing': datapoint.wind('meters_sec').get('deg'),
            'cloud-cover': datapoint.clouds / 100,
            'visibility': datapoint.visibility_distance
        }
        pt_dict.update(temperatures)
        pt_dict.update(feels)
        return pt_dict

    def _process_daily_fc_data(self, data: Forecast) -> pd.DataFrame:
        """Process daily forecast data"""
        cleaned = []
        for pt in data:
            # Extract temperatures (day, min, max, night, eve, morn)
            temps = self._process_temps(pt)
            cleaned.append(self._extract_common_weather_data(pt, temps))
        return pd.DataFrame(cleaned)

    def _process_3h_fc_data(self, data: Forecast) -> pd.DataFrame:
        """Process 3-hour forecast data"""
        cleaned = []
        for pt in data:
            # Extract temperatures (day, min, max, night, eve, morn)
            temps = self._process_temps(pt)
            cleaned.append(self._extract_common_weather_data(pt, temps))
        return pd.DataFrame(cleaned)

    def _process_current_weather_data(self, data: Weather) -> pd.DataFrame:
        """Process current weather data"""
        cleaned = []
        temps = self._process_temps(data)
        cleaned.append(self._extract_common_weather_data(data, temps))
        return pd.DataFrame(cleaned)

    @staticmethod
    def _process_temps(datapoint: Union[Weather, Forecast]) -> Dict[str, float]:
        """Processes the avg/min/max temps"""
        temps_dict = datapoint.temperature('celsius')
        # Remove 'kf' measurements that are sometimes NoneType
        _ = temps_dict.pop('temp_kf', None)
        processed_dict = {}
        for k, v in temps_dict.items():
            # Make a new key that uses kebab case and always has temp as a prefix
            new_k = '-'.join(['temp'] + [x for x in k.replace('temp', '').strip().split('_') if x != ''])
            if new_k == 'temp':
                # Make this key the avg temp key
                new_k = 'temp-avg'
            processed_dict[new_k] = v
        if 'temp-avg' not in processed_dict.keys() and \
                all([x in processed_dict.keys() for x in ['temp-min', 'temp-max']]):
            # Make average from min/max
            processed_dict['temp-avg'] = round((processed_dict['temp-min'] + processed_dict['temp-max']) / 2, 2)

        return processed_dict
