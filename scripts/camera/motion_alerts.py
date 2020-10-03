import os
import tempfile
from datetime import datetime as dt, timedelta
from kavalkilu import Hosts, Log
from servertools import SlackComm, Amcrest, VidTools


logg = Log('motion_alerts', log_to_db=True)
sc = SlackComm()
start_dt = (dt.now() - timedelta(hours=1)).replace(minute=0, second=0)
end_dt = dt.now().replace(minute=0, second=0)


cam_ip = Hosts().get_ip_from_host('ac-v2lis')
cam = Amcrest(cam_ip)
vt = VidTools(640, 360, resize_perc=0.5, speed_x=5)

temp_dir = tempfile.gettempdir()
motion_logs = cam.get_motion_log(start_dt, end_dt)
logg.info(f'Found {len(motion_logs)} motion events from the previous night.')

# Reverse order of list to earliest first
motion_logs.reverse()
buffer = 10  # give the clips an x second buffer before and after motion was detected
files = []
for mlog in motion_logs:
    start = mlog['start'] - timedelta(seconds=10)
    end = mlog['end'] + timedelta(seconds=10)
    logg.info(f'Found motion timerange from {start:%a}: {start:%T} to {end:%T}. Downloading...')
    dl_files = cam.download_files_from_range(start, end, temp_dir)
    logg.debug(f'Found {len(dl_files)} files.')
    # Clip & combine the video files, save to temp file
    logg.debug('Clipping video files and combining them...')
    fpath = vt.make_clip_from_filenames(start, end, dl_files, trim_files=True)
    # Draw rectangles over the motion zones
    logg.debug(f'Detecting motion in downloaded video file...')
    upload, fpath = vt.draw_on_motion(fpath, min_area=800, min_frames=10)
    if upload:
        logg.debug('File is significant... Adding to list.')
        # We have some motion to upload!
        # Add to list of filepaths to be uploaded in bulk
        files.append(fpath)

if len(files) > 0:
    logg.info(f'Uploading {len(files)} vids to channel')
    msg = f'*`{len(files)}`* incoming videos (from *`{len(motion_logs)}`* events) ' \
          f'from `{start_dt:%H:%M}` to `{end_dt:%H:%M}`'
    sc.st.send_message('kaamerad', msg)
    for file in files:
        sc.st.upload_file('kaamerad', file, os.path.split(file)[1])

logg.close()
