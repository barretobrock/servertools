"""Collect forecast data"""
import sys
from datetime import datetime, timedelta
from kavalkilu import LogWithInflux, InfluxDBLocal, InfluxDBHomeAuto
from servertools import OpenWeather, OWMLocation, NWSForecast, NWSForecastZone, \
    YrNoWeather, YRNOLocation


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('forecast', log_dir='weather')
influx = InfluxDBLocal(InfluxDBHomeAuto.WEATHER)
# Number of hours we're looking forward
period_h = 24
# Start & end of the lookahead
p_start = (datetime.now() + timedelta(hours=1))
p_end = (p_start + timedelta(hours=period_h))

try:
    owm_fc = OpenWeather(OWMLocation.ATX).hourly_forecast()
    nws_fc = NWSForecast(NWSForecastZone.ATX).get_hourly_forecast()
    yrno_fc = YrNoWeather(YRNOLocation.ATX).hourly_summary()
except Exception as e:
    log.warning(f'Unable to capture weather info - received error: {e}. Exiting script...')
    log.close()
    sys.exit(1)

# Push all weather data into influx
for svc, df in zip(['own', 'nws', 'yrno'], [owm_fc, nws_fc, yrno_fc]):
    log.debug(f'Collecting data from {svc.upper()}...')
    cols = ['date', 'humidity', 'temp-avg', 'feels-temp-avg']
    if svc == 'nws':
        # Replace relative-humidity with humidity
        df['humidity'] = df['relative-humidity']
    elif svc == 'yrno':
        # No humidity, feelslike included in this one
        _ = [cols.pop(cols.index(x)) for x in ['feels-temp-avg', 'humidity']]
        df['date'] = df['from']
    df = df[cols]
    df = df.rename(columns={x: f'fc-{svc}-{x}' if x != 'date' else x for x in df.columns})
    df = df[(df['date'] >= p_start.strftime('%F %H:00:00')) &
            (df['date'] <= p_end.strftime('%F %H:00:00'))]
    df['loc'] = 'austin'
    influx.write_df_to_table(df, 'loc', df.columns.tolist()[1:-1], 'date')

influx.close()

log.debug('Temp logging successfully completed.')
log.close()
