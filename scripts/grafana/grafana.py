#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pathlib
import time

from grafana_api.grafana_face import GrafanaFace
from kavalkilu import (
    Keys,
    LogWithInflux,
)
import requests

from servertools import SlackComm

log = LogWithInflux('grafana_snapper')
creds = Keys().get_key('grafana')
scom = SlackComm()


def get_pic_and_upload(url, name):
    """Captures dashboard panel at URL and uploads to #notifications slack channel"""

    resp = requests.get(url, headers={'Authorization': f'Bearer {creds["token"]}'})

    temp_file = pathlib.Path().joinpath('/tmp/dash_snap.png')
    with temp_file.open('wb') as f:
        for chunk in resp:
            f.write(chunk)
    scom.st.upload_file(scom.teatede_kanal, temp_file, name)


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


scom.st.send_message(scom.teatede_kanal, 'Daily Report coming up!')
# Use grafana API to get dashboard UID
gapi = GrafanaFace(auth=creds['token'])
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
