"""Collect current weather data"""
from kavalkilu import LogWithInflux, InfluxDBLocal, InfluxDBNames, InfluxTblNames
from servertools import OpenWeather, OWMLocation


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('local', log_dir='weather')
influx = InfluxDBLocal(InfluxDBNames.HOMEAUTO)

current = OpenWeather(OWMLocation.ATX).current_weather()

# Push all weather data into influx
current = current.drop('date', axis=1)
current['loc'] = 'austin'
influx.write_df_to_table(InfluxTblNames.WEATHER, current, 'loc', current.columns.tolist()[:-1])
influx.close()

log.debug('Temp logging successfully completed.')

log.close()
