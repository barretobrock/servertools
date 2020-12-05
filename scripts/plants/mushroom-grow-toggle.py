from kavalkilu import LogWithInflux
from servertools import HueBulb

logg = LogWithInflux('mushroom-grow-toggle')
h = HueBulb('mushroom-plug')

logg.debug('Toggling humidifier...')
h.toggle()

logg.close()
