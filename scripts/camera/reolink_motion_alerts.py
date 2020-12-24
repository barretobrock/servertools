import os
import math
import tempfile
from datetime import datetime as dt, timedelta
from moviepy.editor import VideoFileClip
from kavalkilu import Hosts, LogWithInflux
from easylogger import ArgParse
from servertools import SlackComm, VidTools, Reolink


logg = LogWithInflux('motion_alerts')
sc = SlackComm(parent_log=logg)

args = [
    {
        'names': ['-c', '--camera'],
        'other': {
            'action': 'store',
            'default': 're-v2lis'
        }
    }, {
        'names': ['-i', '--interval'],
        'other': {
            'action': 'store',
            'default': '60'
        }
    }
]
ap = ArgParse(args, parse_all=False)
CAMERA = ap.arg_dict.get('camera')
INTERVAL_MINS = int(ap.arg_dict.get('interval'))
start_dt = (dt.now() - timedelta(minutes=INTERVAL_MINS)).replace(second=0, microsecond=0)
end_dt = (start_dt + timedelta(minutes=INTERVAL_MINS))

cam_ip = Hosts().get_ip_from_host(CAMERA)
cam = Reolink(cam_ip, parent_log=logg)
stream = 'sub'

# Get dimensions of substream
dims = cam.get_dimensions(stream)
logg.debug(f'Video dimensions set to {dims[0]}x{dims[1]}')
vt = VidTools(*dims, resize_perc=1, speed_x=6)

temp_dir = tempfile.gettempdir()
motion_files = cam.get_motion_files(start=start_dt, end=end_dt, streamtype=stream)
logg.info(f'Found {len(motion_files)} motion events for the range selected.')

already_downloaded = []
processed_files = []
durations = []
last_motion_end = None
for mlog in motion_files:
    start = mlog['start']
    end = mlog['end']
    logg.info(f'Found motion timerange from {start:%a}: {start:%T} to {end:%T}.')
    # Search if the time range falls in one of the ranges that were already downloaded
    out_path = os.path.join(temp_dir, mlog['filename'])
    logg.debug('Attempting to download motion file')
    if not cam.get_file(mlog['filename'], out_path):
        logg.warning('Download unsuccessful!')
        continue
    if last_motion_end is not None:
        if start < last_motion_end:
            # Start of this motion event began before the last motion event ended
            #   Adjust the length of the current motion event.
            seconds_from_start = (last_motion_end - start).total_seconds()
            logg.debug(f'Clip overlap detected. Clipping current video by {seconds_from_start} seconds.')
            clip = VideoFileClip(out_path)
            clip = clip.subclip(t_start=seconds_from_start)
            clip.write_videofile(out_path)
    processed_files.append(out_path)
    last_motion_end = end

if len(motion_files) > 0:
    # Clip & combine the video files, save to temp file
    logg.debug('Clipping video files and combining them...')
    fpath = vt.make_clip_from_filenames(motion_files[0]['start'], motion_files[-1]['end'], processed_files,
                                        trim_files=False, prefix=f'{CAMERA}_motion')
    # Draw rectangles over the motion zones
    logg.debug(f'Detecting motion in downloaded video file...')
    upload, fpath, duration = vt.draw_on_motion(fpath, min_area=500, min_frames=10, threshold=20,
                                                ref_frame_turnover=20, buffer_s=0.5)
    if upload:
        logg.info(f'Uploading vid to channel')
        mins = duration / 60
        secs = mins % 1 * 60
        msg = f'*`{CAMERA}`*: *`{len(processed_files)}`* clips out of *`{len(motion_files)}`* motion events ' \
              f'detected from `{start_dt:%H:%M}` to `{end_dt:%H:%M}`\n\t ' \
              f'Total duration: *`{math.floor(mins):.0f}m{secs:.0f}s`*'
        file = vt.concat_files([fpath])
        sc.st.upload_file('kaamerad', file, filename=f'{CAMERA} events', txt=msg)
else:
    logg.info('No significant motion detected during this time interval')

logg.close()
