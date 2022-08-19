"""Collect forecast data"""
from datetime import (
    datetime,
    timedelta,
)

from kavalkilu import (
    InfluxDBHomeAuto,
    InfluxDBLocal,
    LogWithInflux,
)

from servertools import (
    NWSForecast,
    NWSForecastZone,
    OpenWeather,
    OWMLocation,
    YRNOLocation,
    YrNoWeather,
)

# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('forecast', log_dir='weather')
influx = InfluxDBLocal(InfluxDBHomeAuto.WEATHER)
# Number of hours we're looking forward
period_h = 24
# Start & end of the lookahead
p_start = (datetime.now() + timedelta(hours=1))
p_end = (p_start + timedelta(hours=period_h))

service_dict = {
    'owm': {
        'cls': OpenWeather,
        'init-args': [OWMLocation.ATX]
    },
    'nws': {
        'cls': NWSForecast,
        'init-args': [NWSForecastZone.ATX]
    },
    'yrno': {
        'cls': YrNoWeather,
        'init-args': [YRNOLocation.ATX]
    }
}

cols = ['date', 'humidity', 'temp-avg', 'feels-temp-avg']

for svc_name, svc_dict in service_dict.items():
    log.debug(f'Attempting to pull forecast data via {svc_name.upper()} service...')
    try:
        svc = svc_dict.get('cls')(*svc_dict.get('init-args'))
        df = svc.get_hourly_forecast()
    except Exception as e:
        log.warning(f'Exception occurred: {e} - skipping service...')
        continue

    if svc == 'nws':
        # Replace relative-humidity with humidity
        df['humidity'] = df['relative-humidity']
    elif svc == 'yrno':
        # No humidity, but feelslike included in this one
        _ = [cols.pop(cols.index(x)) for x in ['feels-temp-avg', 'humidity']]
        df['date'] = df['from']
    df = df[cols]
    df = df.rename(columns={x: f'fc-{svc}-{x}' if x != 'date' else x for x in df.columns})
    df = df[(df['date'] >= p_start.strftime('%F %H:00:00')) &
            (df['date'] <= p_end.strftime('%F %H:00:00'))]
    df['loc'] = 'austin'
    df['svc'] = svc_name
    log.debug('Writing data to table...')
    influx.write_df_to_table(df=df, tags=['loc', 'svc'], value_cols=df.columns.tolist()[1:-2], time_col='date')

log.debug('Closing influx connection.')
influx.close()

log.debug('Temp logging successfully completed.')
log.close()
