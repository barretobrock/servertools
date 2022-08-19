from datetime import datetime

from kavalkilu import DateTools
from pukr import get_logger
from pylunar import MoonInfo

from servertools import (
    LOG_DIR,
    SlackComm,
)

logg = get_logger('moon_phase', log_dir_path=LOG_DIR.joinpath('weather'))
# lat/long in degrees, mins & secs
loc = ((30, 16, 2), (-97, 44, 35))
mi = MoonInfo(*loc)
dt = DateTools()
scom = SlackComm(parent_log=logg)

now_local = datetime.now()
now_utc = dt.local_time_to_utc(now_local, as_str=False).replace(tzinfo=None)
mi.update(now_utc)
# Get next four phases
full_dt = None
for phase, dt_tuple in mi.next_four_phases():
    if phase == 'full_moon':
        # Correct the seconds
        full_list = list(dt_tuple)
        full_list[-1] = int(round(full_list[-1], 0))
        full_dt = dt.utc_to_local_time(datetime(*full_list)).replace(tzinfo=None)
        break

if full_dt is not None:
    if (full_dt - now_local).days < 2:
        # Announce it in the channel
        scom.st.send_message(scom.ilma_kanal, f'Täiskuu tuleb varsti! {full_dt:%F %T} :full_moon:')

logg.close()
