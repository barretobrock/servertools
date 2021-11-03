"""Collect current weather data"""
import sys
from kavalkilu import LogWithInflux, InfluxDBLocal, InfluxDBHomeAuto
from servertools import YRNOLocation, YrNoWeather


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('local', log_dir='weather')
influx = InfluxDBLocal(InfluxDBHomeAuto.WEATHER)

try:
    current = YrNoWeather(YRNOLocation.ATX).current_summary()
except Exception as e:
    log.warning(f'Unable to capture weather info - received error: {e}. Exiting script...')
    log.close()
    sys.exit(1)

# Push all weather data into influx
current = current.drop(['from', 'to', 'summary', 'wind-bearing', 'wind-speed', 'wind-summary',
                        'precip-intensity', 'pressure'], axis=1)
current['loc'] = 'austin'
influx.write_df_to_table(current, 'loc', current.columns.tolist())
influx.close()

log.debug('Temp logging successfully completed.')

log.close()
