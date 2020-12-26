import time
from typing import Tuple, Optional
from kavalkilu import LogWithInflux, InfluxDBLocal, InfluxDBHomeAuto
from servertools import HueBulb

INTERVAL_MINS = 30
WAIT_S = 290
end_time = time.time() + INTERVAL_MINS * 60
logg = LogWithInflux('mushroom-grow-toggle')
influx = InfluxDBLocal(InfluxDBHomeAuto.TEMPS)
h = HueBulb('mushroom-plug')


def take_measurement() -> Tuple[Optional[float], Optional[float]]:
    query = '''
    SELECT 
        last("temp") AS temp
        , last("humidity") AS hum 
    FROM "temps" 
    WHERE 
        "location" = 'mushroom-station'
        AND time > now() - 30m
    GROUP BY 
        time(1m) 
    ORDER BY time DESC
    '''
    df = influx.read_query(query, 'time').dropna().reset_index()
    if not df.empty:
        return df.loc[0].tolist()[2:]
    return None, None


rounds = 0
while end_time > time.time():
    temp, hum = take_measurement()
    logg.debug(f'Pulled measurements: temp: {temp}, hum: {hum}')
    if hum > 90 and h.on:
        logg.debug('Humidity reached target threshold. Turning off.')
        h.turn_off()
    elif hum < 85 and not h.on:
        logg.debug('Humidity out of safety zone. Turning on.')
        h.turn_on()
    rounds += 1
    logg.debug(f'Waiting {WAIT_S / 60} mins...')
    time.sleep(WAIT_S)

logg.close()
