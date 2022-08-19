from datetime import datetime as dt
import os
import time

from easylogger import ArgParse
from kavalkilu import (
    Hosts,
    LogWithInflux,
    Path,
)

from servertools import (
    Amcrest,
    Reolink,
)

log = LogWithInflux('timelapse')
p = Path()

args = [
    {
        'names': ['-c', '--camera'],
        'other': {
            'action': 'store',
            'default': 'ac-allr6du'
        }
    }
]
ap = ArgParse(args, parse_all=False)
CAMERA = ap.arg_dict.get('camera')
log.debug(f'Using camera {CAMERA}...')
ip = Hosts().get_ip_from_host(CAMERA)
CamObj = Reolink if CAMERA.startswith('re') else Amcrest
pic_dir = p.easy_joiner(p.data_dir, ['timelapse', CAMERA])
if not os.path.exists(pic_dir):
    os.makedirs(pic_dir)
attempts = 5
wait_s = 30

success = False
for i in range(attempts):
    # Take a pic, save it
    try:
        cam = CamObj(ip, parent_log=log)
        fpath = p.easy_joiner(pic_dir, f'{CAMERA}_{dt.now():%F_%T}.png')
        success = cam.snapshot(fpath)
        if success:
            break
        elif p.exists(fpath):
            # Check if the file exists (sometimes a warning code will be sent,
            #   causing success to be False when not perfectly executed.)
            log.debug('Path for snapshot exists. Snap likely had a warning code.')
            success = True
            break
    except Exception as err:
        # Camera on wifi can have shoddy connection.
        # Disregard any errors from the above command and just wait
        log.debug(f'Attempt failed: {err}. Waiting {wait_s}s.')
        if CAMERA.startswith('ac'):
            # Amcrests don't handle so well with WiFi it seems.
            #   Try to perform a reboot to get the camera working properly
            log.info('Performing reboot...')
            cam.camera.reboot()
            time.sleep(80)
        else:
            time.sleep(wait_s)

if not success:
    log.error(f'Not successful at snapping timelapse photo for camera {CAMERA}.')

log.close()
