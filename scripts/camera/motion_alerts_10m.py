import os
import time
import tempfile
from datetime import datetime as dt, timedelta
from kavalkilu import Hosts, Log
from servertools import SlackComm, Amcrest, VidTools

# Interval this script runs
INTERVAL_MIN = 10
logg = Log('motion_alerts', log_to_db=True)
sc = SlackComm()
start_dt = (dt.now() - timedelta(minutes=INTERVAL_MIN)).replace(second=0)
end_dt = dt.now().replace(second=0)


cam_ip = Hosts().get_ip_from_host('ac-v2lis')
cam = Amcrest(cam_ip)
vt = VidTools(640, 360, resize_perc=0.5, speed_x=5)

temp_dir = tempfile.gettempdir()

files = []
logg.info(f'Downloading motion timerange from {start_dt:%a}: {start_dt:%T} to {end_dt:%T}...')
start = time.time()
dl_files = cam.download_files_from_range(start_dt, end_dt, temp_dir)
logg.info(f'Download completed. Took {(time.time() - start) / 60: .2f} minutes.')
logg.debug(f'Found {len(dl_files)} files.')
# Clip & combine the video files, save to temp file
logg.debug('Clipping video files and combining them...')
fpath = vt.make_clip_from_filenames(start_dt, end_dt, dl_files, trim_files=True)
# Draw rectangles over the motion zones
logg.debug(f'Detecting motion in downloaded video file...')
upload, fpath = vt.draw_on_motion(fpath, min_area=500, min_frames=2, threshold=35)
if upload:
    logg.debug('File is significant... Uploading...')
    # We have some motion to upload!
    # Add to list of filepaths to be uploaded in bulk
    sc.st.upload_file('kaamerad', fpath, os.path.split(fpath)[1])
else:
    logg.info('No significant motion detected during this time interval')
logg.close()
