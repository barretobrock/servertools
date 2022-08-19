from datetime import datetime as dt
from datetime import timedelta
import os
import re
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

import amcrest
from kavalkilu import Keys
from loguru import logger
from reolink_api import Camera
import requests
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError

# TODO:
#  - add get_dimensions (sub or main stream) methods to both classes
#  - add means of drawing motion on captured frames inside each class
#       - include an option to clip only frames that have motion with a bit of buffer


class Reolink(Camera):
    """Wrapper for Reolink's Camera class"""
    def __init__(self, ip: str, parent_log: logger = None):
        self.ip = ip
        self.logg = parent_log.bind(child_name=self.__class__.__name__)
        creds = Keys().get_key('webcam')
        super().__init__(self.ip, username=creds['un'], password=creds['pw'])

    def snapshot(self, filepath: str) -> bool:
        """Takes a snapshot - mirrors the similar method in Amcrest,
        though these POE cameras seem to be more stable with regards to connectivity"""
        self.logg.debug('Taking snapshot...')
        img = self.get_snap()
        img.save(filepath)
        return True

    def get_dimensions(self, stream: str = 'sub') -> List[int]:
        """Gets the video dimensions of the camera's stream"""
        dims = self.get_recording_encoding()[0]['initial']['Enc'][f'{stream.lower()}Stream']['size']
        # Split by '*', convert to int
        dims = [int(x) for x in dims.split('*')]
        return dims


class Amcrest:
    """Amcrest camera-related methods"""
    camera_types = {
        'DB': 'doorbell',
        'IPC': 'ip_cam'
    }

    def __init__(self, ip: str, port: int = 80, parent_log: logger = None):
        self.ip = ip
        self.logg = parent_log.bind(child_name=self.__class__.__name__)
        self.creds = Keys().get_key('webcam')
        self.base_url = f'http://{ip}/cgi-bin'
        self.base_url_with_cred = f'http://{self.creds["un"]}:{self.creds["pw"]}@{ip}/cgi-bin'
        self.config_url = f'{self.base_url}/configManager.cgi?action=setConfig'
        try:
            self.camera = amcrest.AmcrestCamera(ip, port, self.creds['un'], self.creds['pw']).camera
            self.is_connected = True
            name = re.search(r'(?<=Name=).*(?=\r)', self.camera.video_channel_title).group()
            model = re.search(r'(?<=type=).*(?=\r)', self.camera.device_type).group()
            camera_type = re.search(r'(?<=class=).*(?=\r)', self.camera.device_class).group()
        except (ConnectionError, amcrest.exceptions.CommError):
            self.camera = None
            self.is_connected = False
            name = model = camera_type = 'unknown'

        if self.camera is not None:
            if camera_type in self.camera_types.keys():
                self.camera_type = self.camera_types[camera_type]
            else:
                self.camera_type = 'other'
            self.is_armed = self.camera.is_motion_detector_on()
            self.is_ptz_enabled = self._check_for_ptz()
        else:
            self.camera_type = 'other'

        self.name = name.lower()
        self.model = model.lower()

    def _check_for_ptz(self) -> bool:
        """Checks if camera is capable of ptz actions"""
        try:
            return True if self.camera.ptz_presets_list() != '' else False
        except amcrest.exceptions.CommError:
            return False

    def _send_request(self, req_str: str):
        """Sends an HTTP request"""
        result = requests.get(req_str, auth=HTTPDigestAuth(self.creds['un'], self.creds['pw']))
        if result.status_code != 200:
            raise Exception('Error in HTTP GET response. Status code: '
                            f'{result.status_code}, Message: {result.text}')

    def toggle_motion(self, set_motion: bool = True):
        """Sets motion detection"""
        if self.camera is None or not self.is_connected:
            return None

        if self.is_armed == set_motion:
            # State is already where we wanted it to be; no need to change
            return None
        motion_val = 'true' if set_motion else 'false'

        motion_url = f'{self.config_url}&MotionDetect[0].Enable={motion_val}'
        self._send_request(motion_url)

    def set_ptz_flag(self, armed: bool):
        """Orients PTZ-enabled cameras either to armed position (1) or disarmed (2)"""

        if self.is_ptz_enabled:
            # This is likely PTZ-enabled
            # Set to target flag
            preset_pt = 1 if armed else 2
            resp = self.camera.go_to_preset(action='start', preset_point_number=preset_pt)
            if resp[:2] != 'OK':
                # Something went wrong. Raise exception so it gets logged
                raise Exception(f'Camera "{self.name}" PTZ call '
                                f'saw unexpected response: "{resp}"')

    def get_current_ptz_coordinates(self) -> Optional[str]:
        """Gets the current xyz coordinates for a PTZ-enabled camera"""
        if self.is_ptz_enabled:
            ptz_list = self.camera.ptz_status().split('\r\n')[2:5]
            return ','.join([x.split('=')[1] for x in ptz_list])

    def arm_camera(self, armed: bool = True):
        """Wrapper method that both arms the motion detection setting
        as well as orients a PTZ enabled camera to the ARMED position"""
        if self.camera is None:
            return None

        self.toggle_motion(armed)
        if self.is_ptz_enabled:
            self.set_ptz_flag(armed)

    def snapshot(self, filepath: str) -> bool:
        """Takes a snapshot using the main stream (0)"""
        self.logg.debug('Getting snapshot...')
        res = self.camera.snapshot(0, filepath)
        self.logg.debug(f'Response from snapshot: {res.status}')
        if res.status != 200:
            return False
        return True

    @staticmethod
    def _consolidate_events(events: List[Dict[str, Union[str, dt]]], limit_s: int = 60,
                            default_s: int = 60) -> Optional[List[Dict[str, dt]]]:
        """Takes in a list of motion events and consolidates them if they're within range of each other
        Args:
            limit_s: limit in seconds, after which two events are actually considered separate
            default_s: if no start/end time provided, the end with be this amount of seconds
                added to the missing start/end time
        """
        # First step is to pair event starts and ends
        new_event = {}
        new_events = []
        for event in events:
            if all([x in new_event.keys() for x in ['start', 'end']]):
                # All keys have been added. Append to the list
                new_events.append(new_event)
                new_event = {}
            if len(new_event.keys()) == 0:
                # New dict
                if event['type'] == 'Event End':
                    # Event end before begin; this likely means a motion event started
                    #   before our time range. Use default lookbehind to estimate the event start
                    new_event['start'] = event['time'] - timedelta(seconds=default_s)
            start_or_end = 'start' if 'Begin' in event['type'] else 'end'
            # Populate common parts of event info
            new_event.update({
                start_or_end: event['time'],
                'region': event['detail.region-name'].lower(),
                'channel': int(event['detail.channel-no.']),
                'event-type': event['detail.event-type'].lower()
            })
        if len(new_event) != 0:
            # Make sure we also have an end to this last event
            if 'end' not in new_event.keys():
                new_event['end'] = new_event['start'] + timedelta(seconds=default_s)
            new_events.append(new_event)

        # Now combine individual events if they occur within {limit_s} to each other
        combi_event = {'event-list': []}
        combi_events = []
        prev_event_end = None
        if len(new_events) == 0:
            return []
        for event in new_events:
            # Calculate the diff
            if prev_event_end is not None:
                diff = (event['start'] - prev_event_end).seconds
            else:
                # First event
                diff = 0
            # Compare diff; determine whether to combine
            if diff <= limit_s:
                # Combine current start and previous end
                combi_event['event-list'].append(event)
            else:
                # diff exceeds limit; split into another combi event
                combi_event.update({
                    'start': min([x['start'] for x in combi_event['event-list']]),
                    'end': max([x['end'] for x in combi_event['event-list']])
                })
                combi_events.append(combi_event)
                # Reset dict
                combi_event = {
                    'event-list': [event]
                }
            prev_event_end = event['end']

        if len(combi_event['event-list']) > 0:
            # Info remaining in combi_event
            combi_event.update({
                'start': min([x['start'] for x in combi_event['event-list']]),
                'end': max([x['end'] for x in combi_event['event-list']])
            })
            combi_events.append(combi_event)

        return combi_events

    def get_motion_log(self, start_dt: dt, end_dt: dt) -> List[dict]:
        """Returns log of motion detection events between two timestamps"""
        # Get logs for given range
        #   Amcrest does a kind of tokenization that allows us to grab
        #   logs in batches of 100. Tokens seem to be just sequential ints
        #   and are not page numbers! Once the end of the log is reached,
        #   the 'found' variable will be 0.
        raw_token = self.camera.log_find_start(start_dt, end_dt)
        token = re.search(r'(?!token=)\d+', raw_token).group(0)

        events = []
        item_dict = {}
        cur_item_no = 0
        while True:
            log_batch = self.camera.log_find_next(token, count=100)
            raw_logs = log_batch.split('\r\n')
            batch_size = int(re.search(r'(?!found=)\d+', log_batch).group(0))
            if batch_size == 0:
                break
            # Sift through logs, build out events
            for logstr in raw_logs:
                # Make sure we're getting an item and not any other info
                if re.search(r'(?<=items\[)\d+', logstr):
                    # Get item number
                    item_no = int(re.search(r'(?<=items)\[(\d+)]', logstr).group(1))
                    # Get & clean the name of the item
                    item_name = re.search(r'(?<=]\.).*(?==)', logstr).group(0).lower().replace(' ', '-')
                    item_name = re.sub(r'\[\d+]', '', item_name)
                    # The value after the item name
                    item_value = re.search(r'(?<==).*', logstr).group(0)
                    if item_name == 'time':
                        # Convert to datetime
                        item_value = dt.strptime(item_value, '%Y-%m-%d %H:%M:%S')
                    if item_no != cur_item_no:
                        # New item - move item dict to events and initiate new one
                        events.append(item_dict)
                        item_dict = {item_name: item_value}
                        cur_item_no = item_no
                    else:
                        # Same item - add to existing dict
                        item_dict[item_name] = item_value

        # Of the events that are motion related
        mevents = [x for x in events if x.get('detail.event-type', '') == 'Motion Detect']
        # Reverse the order of events so they're chronological
        mevents.reverse()

        return self._consolidate_events(mevents)

    @staticmethod
    def extract_timestamp(fpath: str) -> str:
        """Extracts a timestamp from the filepath"""
        final = []
        regex = [
            r'(?<=\/sd\/)\d{4}(-\d{2}){2}',
            r'(?<=\/dav\/\d{2}\/)\d{2}(\.\d{2}){2}-\d{2}(\.\d{2}){2}'
        ]
        for rgx in regex:
            match = re.search(rgx, fpath)
            if match is not None:
                final.append(match.group())

        return '_'.join(final).replace('.', ':')

    def download_files_from_range(self, start_dt: dt, end_dt: dt,
                                  temp_dir: str) -> List[dict]:
        """Downloads mp4 files from a set datetime range"""
        file_dicts = []
        for text in self.camera.find_files(start_dt, end_dt):
            for line in text.split('\r\n'):
                key, value = list(line.split('=', 1) + [None])[:2]
                if key.endswith('.FilePath'):
                    if value.endswith('.mp4'):
                        ts = self.extract_timestamp(value)
                        dt_objs = []
                        date_dt = dt.strptime(ts.split('_')[0], '%Y-%m-%d')
                        for t in ts.split('_')[1].split('-'):
                            dt_objs.append(dt.combine(date_dt, dt.strptime(t, '%H:%M:%S').time()))
                        new_filename = f'{ts}.mp4'
                        fpath = os.path.join(temp_dir, new_filename)
                        file_dicts.append({
                            'start': dt_objs[0],
                            'end': dt_objs[1],
                            'path': fpath
                        })
                        with open(fpath, 'wb') as f:
                            f.write(self.camera.download_file(value))
        return file_dicts

    def get_video_stream(self, channel: int = 0, subtype: int = 1) -> str:
        """
        Outputs the video stream url
        Args:
            channel: int, which channel to use. default = 0
            subtype: int, stream type to use. 0 = main, 1 = extra_1, etc
                default = 1

        Returns:
            str, the url to the stream
        """
        return f'{self.base_url_with_cred}/mjpg/video.cgi?channel={channel}&subtype={subtype}'
