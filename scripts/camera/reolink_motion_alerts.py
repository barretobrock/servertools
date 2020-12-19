import os
import tempfile
from datetime import datetime as dt, timedelta
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
cam = Reolink(cam_ip)
stream = 'sub'

# Get dimensions of substream
dims = cam.get_dimensions(stream)
logg.debug(f'Video dimensions set to {dims[0]}x{dims[1]}')
vt = VidTools(*dims, resize_perc=1, speed_x=6)

temp_dir = tempfile.gettempdir()
motion_files = cam.get_motion_files(start=start_dt, end=end_dt, streamtype=stream)
logg.info(f'Found {len(motion_files)} motion events for the range selected.')

already_downloaded = []
files = []
durations = []
for mlog in motion_files:
    start = mlog['start']
    end = mlog['end']
    logg.info(f'Found motion timerange from {start:%a}: {start:%T} to {end:%T}.')
    # Search if the time range falls in one of the ranges that were already downloaded
    out_path = None
    if not any([all([x['start'] < start < x['end'], end < x['end']]) for x in already_downloaded]):
        # Check if start time is already covered
        clip_st = start
        clip_end = end
        for dl_dict in already_downloaded:
            if dl_dict['start'] < start < dl_dict['end']:
                # Top-end of range already covered
                clip_st = (dl_dict['end'] + timedelta(seconds=1))
            if dl_dict['start'] < end < dl_dict['end']:
                # Bottom-end of range already covered
                clip_end = (dl_dict['start'] - timedelta(seconds=1))
        logg.debug(f'Downloading file(s) covering {clip_st:%T} to {clip_end:%T}..')

        out_path = os.path.join(temp_dir, mlog['filename'])
        if cam.get_file(mlog['filename'], out_path):
            already_downloaded.append({
                'start': clip_st,
                'end': clip_end,
                'path': out_path
            })
    if out_path is None:
        continue
    # Clip & combine the video files, save to temp file
    logg.debug('Clipping video files and combining them...')
    fpath = vt.make_clip_from_filenames(start, end, [out_path], trim_files=False, prefix=f'{CAMERA}_motion')
    # Draw rectangles over the motion zones
    logg.debug(f'Detecting motion in downloaded video file...')
    upload, fpath, duration = vt.draw_on_motion(fpath, min_area=500, min_frames=2, threshold=20,
                                                ref_frame_turnover=20, buffer_s=0.5)
    if upload:
        logg.debug('File is significant... Adding to list.')
        # We have some motion to upload!
        # Add to list of filepaths to be uploaded in bulk
        files.append(fpath)
        durations.append(duration)

if len(files) > 0:
    logg.info(f'Uploading {len(files)} vids to channel')
    mins = sum(durations) / 60
    secs = mins % 1 * 60
    msg = f'*`{CAMERA}`*: *`{len(files)}`* clips out of *`{len(motion_files)}`* motion events ' \
          f'detected from `{start_dt:%H:%M}` to `{end_dt:%H:%M}`\n\t ' \
          f'Total duration: *`{mins:.0f}m{secs:.0f}s`*'
    file = vt.concat_files(files)
    sc.st.upload_file('kaamerad', file, filename=f'{CAMERA} events', txt=msg)
else:
    logg.info('No significant motion detected during this time interval')

logg.close()
