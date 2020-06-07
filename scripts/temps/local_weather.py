"""Collect weather data from DarkSky"""
from kavalkilu import Log
from servertools import NWSForecast, NWSForecastZone


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('local', log_dir='temps')
latlong_dict = {
    'darksky_austin': '30.3428,-97.7582',
    'darksky_tallinn': '59.4040,24.6540',
    'darksky_rakvere': '59.3311,26.2880',
}

# Instantiate the sensor wrapper for each location & update values.
for location, latlong in latlong_dict.items():
    dsky_wrapper = DarkSkyWeatherSensor(DarkSkyWeather(latlong))
    sl = SensorLogger(location, dsky_wrapper)
    sl.update(openhab=False)

log.debug('Temp logging successfully completed.')

log.close()
