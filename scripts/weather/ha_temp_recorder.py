"""Sends latest temperature readings to HASS"""
from kavalkilu import LogWithInflux, InfluxDBHomeAuto, InfluxDBLocal, HAHelper


log = LogWithInflux('ha-temps', log_dir='weather')
influx = InfluxDBLocal(InfluxDBHomeAuto.TEMPS)

query = '''
    SELECT 
        last("temp")
    FROM "temps" 
    WHERE 
        location =~ /mushroom|r6du|elutuba|wc|v2lis|freezer|fridge|kontor/
        AND time > now() - 30m
    GROUP BY 
        "location" 
    fill(null)
    ORDER BY ASC
'''
df = influx.read_query(query, time_col='time')
log.debug(f'Collected {df.shape[0]} rows of data')

log.debug('Beginning to send updates to HASS')
ha = HAHelper()
for i, row in df.iterrows():
    loc_name = row['location'].replace('-', '_')
    dev_name = f'sensor.{loc_name}_temp'
    log.debug(f'Updating {dev_name}...')
    ha.set_state(dev_name, data={'state': row['last']}, data_class='temp')
log.debug('Update completed.')

log.close()
