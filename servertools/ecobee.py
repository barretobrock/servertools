from pytz import timezone
from datetime import datetime
import pandas as pd
from pyecobee import EcobeeService, SelectionType, Selection
from kavalkilu import Keys


class EcoBee:
    def __init__(self):
        creds = Keys().get_key('ecobee')
        app_key = creds['app-key']
        # Device serial number
        self.sn = creds['serial']
        # Connect to the service
        self.service = EcobeeService('Home', app_key)
        # Get auth tokens
        self.auth_protocol()

    def auth_protocol(self):
        """The entire authorization protocol"""
        auth_resp = self.service.authorize()
        self._request_tokens()

    def _request_tokens(self):
        """Request auth tokens"""
        # TODO - figure out error protocol here; when to call _refresh_tokens()
        token_resp = self.service.request_tokens()

    def _refresh_tokens(self):
        """Refresh auth tokens"""
        token_resp = self.service.refresh_tokens()

    def collect_data(self, start_dt: datetime, end_dt: datetime, tz_name: str = 'US/Central') -> pd.DataFrame:
        """Collects usage info from Ecobee, converts temps to C and outputs as pandas DataFrame"""
        tz = timezone(tz_name)

        # Select device by serial number
        dev = Selection(
            selection_type=SelectionType.THERMOSTATS.value,
            selection_match=self.sn
        )

        # Collect the raw data
        runtime_report_response = self.service.request_runtime_reports(
            selection=dev,
            start_date_time=tz.localize(start_dt),
            end_date_time=tz.localize(end_dt),
            columns='auxHeat1,compCool1,compHeat1,economizer,fan,humidifier'
                    ',hvacMode,ventilator,zoneAveTemp,zoneClimate,zoneCoolTemp'
                    ',zoneHeatTemp,zoneHumidity')

        report_cols = runtime_report_response.columns.split(',')
        # Add in date, time columns and an offset column
        data_cols = ['date', 'time'] + report_cols + ['offset']

        data_row = runtime_report_response.report_list[0]
        df = pd.DataFrame(
            data=[x.split(',') for x in data_row.row_list],
            columns=data_cols
        )

        return df

    @staticmethod
    def _convert_temp_cols(df: pd.DataFrame) -> pd.DataFrame:
        """Converts the Fahrenheit columns in a dataframe to Celsius"""
        for col in df.columns.tolist():
            if 'Temp' in col:
                df[col] = df[col].apply(lambda x: (x - 32) * (5.0 / 9.0))

        return df
