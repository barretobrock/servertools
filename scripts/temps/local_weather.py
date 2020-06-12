"""Collect weather data from DarkSky"""
from kavalkilu import Log
from servertools import NWSForecast, NWSForecastZone


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('local', log_dir='temps')



# Instantiate the sensor wrapper for each location & update values.
for location, latlong in latlong_dict.items():
    dsky_wrapper = DarkSkyWeatherSensor(DarkSkyWeather(latlong))
    sl = SensorLogger(location, dsky_wrapper)
    sl.update(openhab=False)

log.debug('Temp logging successfully completed.')

log.close()
