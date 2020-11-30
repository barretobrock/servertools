import tempfile
from datetime import datetime as dt, timedelta
from kavalkilu import Hosts, LogWithInflux, ArgParse
from servertools import SlackComm, Amcrest, VidTools


logg = LogWithInflux('motion_alerts')
sc = SlackComm()

args = [
    {
        'names': ['-c', '--camera'],
        'other': {
            'action': 'store',
            'default': 'ac-v2lis'
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
cam = Amcrest(cam_ip)
vt = VidTools(640, 360, resize_perc=0.5, speed_x=5)

temp_dir = tempfile.gettempdir()
motion_logs = cam.get_motion_log(start_dt, end_dt)
logg.info(f'Found {len(motion_logs)} motion events for the range selected.')

buffer = 30  # give the clips an x second buffer before and after motion was detected

already_downloaded = []
files = []
for mlog in motion_logs:
    start = mlog['start'] - timedelta(seconds=buffer)
    end = mlog['end'] + timedelta(seconds=buffer)
    logg.info(f'Found motion timerange from {start:%a}: {start:%T} to {end:%T}.')
    # Search if the time range falls in one of the ranges that were already downloaded
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
        already_downloaded += cam.download_files_from_range(clip_st, clip_end, temp_dir)

    filepaths = list(sorted(set([x['path'] for x in already_downloaded
                                 if x['start'] < start < x['end'] or x['start'] < end < x['end']])))
    # Clip & combine the video files, save to temp file
    logg.debug('Clipping video files and combining them...')
    fpath = vt.make_clip_from_filenames(start, end, filepaths, trim_files=True,
                                        prefix=f'{CAMERA}_motion')
    # Draw rectangles over the motion zones
    logg.debug(f'Detecting motion in downloaded video file...')
    upload, fpath = vt.draw_on_motion(fpath, min_area=500, min_frames=2, threshold=20)
    if upload:
        logg.debug('File is significant... Adding to list.')
        # We have some motion to upload!
        # Add to list of filepaths to be uploaded in bulk
        files.append(fpath)

if len(files) > 0:
    logg.info(f'Uploading {len(files)} vids to channel')
    msg = f'{len(files)} clips out of {len(motion_logs)} motion events detected from {start_dt:%T} to {end_dt:%T}'
    file = vt.concat_files(files)
    sc.st.upload_file('kaamerad', file, msg)
else:
    logg.info('No significant motion detected during this time interval')

logg.close()
