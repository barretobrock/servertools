import time
from kavalkilu import LogWithInflux
from servertools import HueBulb

INTERVAL_MINS = 30
ON_TIME_WEIGHT = 1 / 3
OFF_TIME_WEIGHT = 1 - ON_TIME_WEIGHT

logg = LogWithInflux('mushroom-grow-toggle')
h = HueBulb('mushroom-plug')
n_rounds = int(60 / INTERVAL_MINS)

on_period_secs = INTERVAL_MINS * 60 * ON_TIME_WEIGHT
off_period_secs = INTERVAL_MINS * 60 * OFF_TIME_WEIGHT

for x in range(0, n_rounds):
    h.turn_on()
    logg.debug(f'Turning on humidifier. Waiting {on_period_secs / 60:.0f} mins')
    time.sleep(on_period_secs)
    logg.debug(f'Turning off humidifier. Waiting {off_period_secs / 60:.0f} mins...')
    h.turn_off()
    time.sleep(off_period_secs)

logg.close()
