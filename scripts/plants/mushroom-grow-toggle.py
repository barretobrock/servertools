import time
from kavalkilu import LogWithInflux, InfluxDBLocal, InfluxDBHomeAuto
from servertools import HueBulb

INTERVAL_MINS = 30
WAIT_S = 290
end_time = time.time() + INTERVAL_MINS * 60
logg = LogWithInflux('mushroom-grow-toggle')
influx = InfluxDBLocal(InfluxDBHomeAuto.TEMPS)
h = HueBulb('mushroom-plug')
# TODO: Use HASS instead of Influx to get current values


rounds = 0
while end_time > time.time():
    if rounds % 2 == 0:
        # Turn on during even rounds
        h.turn_on()
    else:
        # Turn off for off rounds
        h.turn_off()
    rounds += 1
    logg.debug(f'Waiting {WAIT_S / 60:.0f} mins...')
    time.sleep(WAIT_S)

logg.close()
