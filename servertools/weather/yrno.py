import pandas as pd
from yr.libyr import Yr


class YRNOLocation:
    """Locations for YRNO"""
    ATX = 'USA/Texas/Austin'
    TLL = 'Estonia/Harjumaa/Tallinn'
    RKV = 'Estonia/Lääne-Virumaa/Rakvere'


class YrNoWeather:
    """Pulls weather data using Yr.no weather API"""
    def __init__(self, location: str, timezone: str = 'US/Central'):
        """
        Args:
            location(str): location name `country/region/city`
            timezone(str):  time zone to record time
        """
        self.location = location
        self.tz = timezone

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

    def get_current_summary(self) -> pd.DataFrame:
        """Collect the current weather data for the location"""
        data = Yr(location_name=self.location).now()
        cleaned = pd.DataFrame(self._process_data(data), index=[1])
        return cleaned

    def get_hourly_forecast(self) -> pd.DataFrame:
        """Creates a 48 hour forecast summary"""
        data = Yr(location_name=self.location, forecast_link='forecast_hour_by_hour')
        return pd.DataFrame([self._process_data(x) for x in data.forecast()])

    def get_daily_forecast(self) -> pd.DataFrame:
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
