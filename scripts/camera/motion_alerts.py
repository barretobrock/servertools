import os
from datetime import datetime as dt, timedelta
import tempfile
from kavalkilu import Hosts, Log
from servertools import SlackComm, Amcrest, VidTools


logg = Log('motion_alerts', log_to_db=True)
sc = SlackComm()
start_dt = (dt.now() - timedelta(hours=3)).replace(minute=0, second=0)
end_dt = dt.now().replace(minute=0, second=0)


cam_ip = Hosts().get_ip_from_host('ac-v2lis')
cam = Amcrest(cam_ip)
vt = VidTools(640, 360, resize_perc=0.5, speed_x=6)

temp_dir = tempfile.gettempdir()
temp_mp4_fpath = os.path.join(temp_dir, 'temp.mp4')

motion_logs = cam.get_motion_log(start_dt, end_dt)
logg.info(f'Found {len(motion_logs)} motion events from the previous night.')

if len(motion_logs) > 0:
    sc.st.send_message('kaamerad', f'{len(motion_logs)} incoming motion events from '
                                   f'({start_dt:%T} to {end_dt:%T})!')
# Reverse order of list to earliest first
motion_logs.reverse()
buffer = 10  # give the clips an x second buffer before and after motion was detected
for mlog in motion_logs:
    start = mlog['start'] - timedelta(seconds=10)
    end = mlog['end'] + timedelta(seconds=10)
    logg.info(f'Found motion timerange from {start:%a}: {start:%T} to {end:%T}')
    logg.debug('Downloading files...')
    dl_files = cam.download_files_from_range(start, end, temp_dir)
    logg.debug(f'Found {len(dl_files)} files.')
    # Clip & combine the video files, save to temp file
    logg.debug('Clipping video files and combining them...')
    vt.make_clip_from_filenames(start, end, dl_files, trim_files=True)
    # Draw rectangles over the motion zones
    logg.debug(f'Detecting motion in downloaded video file...')
    upload = vt.draw_on_motion(min_area=600)
    if upload:
        # We have some motion to upload!
        final_fname = f'motion_{start:%F_%T}_to_{end:%F_%T}.mp4'
        logg.info(f'Uploading vid to channel: {final_fname}')
        sc.st.upload_file('kaamerad', vt.temp_mp4_out_fpath, final_fname)

logg.close()
