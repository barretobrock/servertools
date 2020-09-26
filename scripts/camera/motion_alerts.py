import os
from datetime import datetime as dt, timedelta
from kavalkilu import Hosts, Log
from servertools import SlackComm, Amcrest


logg = Log('motion_alerts', log_to_db=True)
sc = SlackComm()
start_dt = (dt.today() - timedelta(days=1)).replace(hour=20, minute=0, second=0)
end_dt = dt.today().replace(hour=7, minute=0, second=0)

cam_ip = Hosts().get_ip_from_host('ac-v2lis')
cam = Amcrest(cam_ip)

motion_logs = cam.get_motion_log(start_dt, end_dt)
# Reverse order of list
motion_logs.reverse()
for mlog in motion_logs:
    gif_path = cam.get_gif_for_range(mlog['start'], mlog['end'])
    gif_fname = os.path.split(gif_path)[1]
    logg.info(f'Uploading gif to channel: {gif_fname}')
    sc.st.upload_file('kaamerad', gif_path, gif_fname)

logg.close()
