"""Collect current weather data"""
from kavalkilu import LogWithInflux, InfluxDBLocal, InfluxDBHomeAuto
from servertools import YRNOLocation, YrNoWeather


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('local', log_dir='weather')
influx = InfluxDBLocal(InfluxDBHomeAuto.WEATHER)

current = YrNoWeather(YRNOLocation.ATX).current_summary()

# Push all weather data into influx
current = current.drop(['from', 'to', 'summary', 'wind-bearing', 'wind-speed', 'wind-summary',
                        'precip-intensity', 'pressure'], axis=1)
current['loc'] = 'austin'
influx.write_df_to_table(current, 'loc', current.columns.tolist())
influx.close()

log.debug('Temp logging successfully completed.')

log.close()
