import amcrest
import requests
import re
import os
import tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips
from datetime import datetime as dt, timedelta
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError
from typing import Optional, List
from kavalkilu import Keys


class Amcrest:
    """Amcrest camera-related methods"""
    camera_types = {
        'DB': 'doorbell',
        'IPC': 'ip_cam'
    }

    def __init__(self, ip: str, port: int = 80):
        self.ip = ip
        self.creds = Keys().get_key('webcam_api')
        self.base_url = f'http://{ip}/cgi-bin'
        self.base_url_with_cred = f'http://{self.creds["user"]}:{self.creds["password"]}@{ip}/cgi-bin'
        self.config_url = f'{self.base_url}/configManager.cgi?action=setConfig'
        try:
            self.camera = amcrest.AmcrestCamera(ip, port, self.creds['user'], self.creds['password']).camera
            self.is_connected = True
            name = re.search(r'(?<=Name=).*(?=\r)', self.camera.video_channel_title).group()
            model = re.search(r'(?<=type=).*(?=\r)', self.camera.device_type).group()
            camera_type = re.search(r'(?<=class=).*(?=\r)', self.camera.device_class).group()
        except (ConnectionError, amcrest.exceptions.CommError) as e:
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
        result = requests.get(req_str, auth=HTTPDigestAuth(self.creds['user'], self.creds['password']))
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

    @staticmethod
    def _consolidate_events(events: List[dict], limit_s: int = 60) -> List[dict]:
        """Takes in a list of motion events and consolidates them if they're within range of each other"""
        new_events = []
        prev_event_end = None
        event_start = None
        for event in events:
            if len(event.keys()) < 2:
                continue
            if prev_event_end is not None:
                diff = (prev_event_end - event['start']).seconds
            else:
                diff = 0
                prev_event_end = event['end']
            if diff < limit_s:
                # Combine current start and previous end
                event_start = event['start']
            else:
                # diff exceeds limit; split
                new_events.append({'start': event_start, 'end': prev_event_end})
                event_start = event['start']
                prev_event_end = event['end']

        if prev_event_end is None:
            # Started over without saving the last event
            new_events.append(event)
        else:
            new_events.append({'start': event_start, 'end': prev_event_end})
        return new_events

    def get_motion_log(self, start_dt: dt, end_dt: dt) -> List[dict]:
        """Returns log of motion detection events between two timestamps"""
        # Get log for given range
        logresp = next(self.camera.log_find(start_dt, end_dt))
        # Split by return char combo
        logs = logresp.split('\r\n')
        # Sift through logs, build out events
        events = []
        item_dict = {}
        event_time = None
        for logstr in logs:
            item_match = re.search(r'(?<=items\[)\d+', logstr)
            if item_match is not None:
                # Found an item
                if 'Time=' in logstr:
                    # Capture event time
                    event_time = re.search(r'(?<=Time=)[\d\s\-:]+', logstr).group()
                elif '.Type=Event' in logstr:
                    # Capture whether this was an event start or end
                    event_type = re.search(r'(?<=Type=Event\s)\w+', logstr).group().lower()
                    # Replace begin with start
                    event_type = event_type.replace('begin', 'start')
                    if event_type in item_dict.keys():
                        # Event was already in item dict, so must be...
                        # New event
                        events.append(item_dict)
                        item_dict = {}
                    # Add to dict
                    item_dict[event_type] = dt.strptime(event_time, '%Y-%m-%d %H:%M:%S')
                    if all([x in item_dict.keys() for x in ['start', 'end']]):
                        # Full dict
                        events.append(item_dict)
                        item_dict = {}

        return self._consolidate_events(events)

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

    def get_gif_for_range(self, start_dt: dt, end_dt: dt, buffer_s: int = 30, resize_perc: float = 0.5,
                          speed_x: int = 6) -> str:
        """For a given range, retrieves the video (mp4) and converts to gif.
        Returns the path to the saved gif"""
        # TODO: test that a range sub the 5min interval retrieves a single mp4 file
        temp_dir = tempfile.gettempdir()
        start_dt = start_dt - timedelta(seconds=buffer_s)
        end_dt = end_dt + timedelta(seconds=buffer_s)
        # Pull the files associated with the timerange provided
        dl_files = []
        for text in self.camera.find_files(start_dt, end_dt):
            for line in text.split('\r\n'):
                key, value = list(line.split('=', 1) + [None])[:2]
                if key.endswith('.FilePath'):
                    if value.endswith('.mp4'):
                        new_filename = f'{self.extract_timestamp(value)}.mp4'
                        fpath = os.path.join(temp_dir, new_filename)
                        dl_files.append(fpath)
                        with open(fpath, 'wb') as f:
                            f.write(self.camera.download_file(value))
        # Now go through the downloaded files and combine them
        clips = []
        for dl_file in dl_files:
            # TODO: Determine how to subclip
            # 1. get seconds from clip start to motion start
            # 2. get seconds from clip end to motion end
            # 3. add as subclip((secs_from_start: float), (secs_from_end: float))
            clip_ymd = re.search(r'\d{4}-\d{2}-\d{2}', dl_file).group()
            clip_st, clip_end = [dt.strptime(f'{clip_ymd} {x[0]}', '%Y-%m-%d %H:%M:%S')
                                 for x in re.findall(r'((\d+:){2}\d{2})', dl_file)]
            # Determine if we need to crop the clip at all
            secs_from_start = (start_dt - clip_st).seconds if start_dt > clip_st else 0
            secs_from_end = -1 * (clip_end - end_dt).seconds if clip_end > end_dt else None
            clip = (VideoFileClip(dl_file).subclip(secs_from_start, secs_from_end).resize(resize_perc).speedx(speed_x))
            # Append to our clips
            clips.append(clip)
        # Concatenate all the clips
        all_clips = concatenate_videoclips(clips)
        # Write to gif
        outfile = f'motion_gif_{start_dt:%F_%T}_to_{end_dt:%F_%T}.gif'
        outpath = os.path.join(temp_dir, outfile)
        all_clips.write_gif(outpath, fps=2, fuzz=10)
        return outpath

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
