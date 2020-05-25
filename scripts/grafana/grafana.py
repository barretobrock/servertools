#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import requests
from grafana_api.grafana_face import GrafanaFace
from kavalkilu import Keys, Log, LogArgParser
from kavalkilu.local_tools import slack_comm, notify_channel


log = Log('grafana_snapper', log_lvl=LogArgParser().loglvl)
get_key = Keys().get_key
creds = get_key('grafana-api')


def get_pic_and_upload(url, name):
    """Captures dashboard panel at URL and uploads to #notifications slack channel"""

    resp = requests.get(url, headers={'Authorization': 'Bearer {}'.format(creds['key'])})

    temp_file = os.path.abspath('/tmp/dash_snap.png')
    with open(temp_file, 'wb') as f:
        for chunk in resp:
            f.write(chunk)
    slack_comm.upload_file(notify_channel, temp_file, name)


# The URL template to use
base_url = 'http://{host}/render/{name}?orgId=1&from={from}&to={to}&panelId={pid}&width=1000&height=500'

# time range to snap
now = time.time() * 1000
then = now - 24 * 60 * 60 * 1000

url_dict = {
    'host': creds['host'],
    'from': round(then),
    'to': round(now)
}

# Panels to grab snapshots of
snap_panels = [
    'Temperatures', 'Logged Output over Time', 'Log Output by Log Name',
    'Download Speeds', 'Upload Speeds'
]


slack_comm.send_message(notify_channel, 'Daily Report coming up!')
# Use grafana API to get dashboard UID
gapi = GrafanaFace(auth=creds['key'], host=creds['host'])
for dash_tag in ['home_automation', 'speedtests', 'logs', 'pihole']:
    dash_info = gapi.search.search_dashboards(tag=dash_tag)
    if len(dash_info) > 0:
        dash_uid = dash_info[0]['uid']
        dash_name = dash_info[0]['url'].replace('/d/', 'd-solo/')
        url_dict.update({'name': dash_name})
        dash = gapi.dashboard.get_dashboard(dash_uid)
        panels = dash['dashboard']['panels']
        for panel in panels:
            if panel['title'] in snap_panels:
                url_dict.update({'pid': panel['id']})
                get_pic_and_upload(base_url.format(**url_dict), panel['title'])


log.close()
