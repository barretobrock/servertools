import amcrest
import requests
import re
import os
import numpy as np
import cv2
import imutils
import tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageSequenceClip
from datetime import datetime as dt, timedelta
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError
from typing import Optional, List, Dict, Tuple, Union
from kavalkilu import Keys


class GIFTools:
    """Class for handling GIFs"""
    pass


class VidTools:
    """Class for general video editing"""
    temp_dir = tempfile.gettempdir()
    # temp_mp4_in_fpath = os.path.join(temp_dir, 'tempin.mp4')
    # temp_mp4_out_fpath = os.path.join(temp_dir, 'tempout.mp4')
    fps = 20
    resize_perc = 0.5
    speed_x = 6

    def __init__(self, vid_w: int = 640, vid_h: int = 360, fps: int = None, resize_perc: float = None,
                 speed_x: int = None):
        if fps is not None:
            self.fps = fps
        if resize_perc is not None:
            self.resize_perc = resize_perc
        if speed_x is not None:
            self.speed_x = speed_x
        self.vid_w = vid_w
        self.vid_h = vid_h

    @staticmethod
    def _get_trim_range_from_filename(fpath: str, start: dt, end: dt) -> Tuple[int, int]:
        """Looks at the filename, returns a start and end time to trim the clip with
            based on the required start and end dates
        """
        # 1. get seconds from clip start to motion start
        # 2. get seconds from clip end to motion end
        # 3. add as subclip((secs_from_start: float), (secs_from_end: float))
        clip_ymd = re.search(r'\d{4}-\d{2}-\d{2}', fpath).group()
        clip_st, clip_end = [dt.strptime(f'{clip_ymd} {x[0]}', '%Y-%m-%d %H:%M:%S')
                             for x in re.findall(r'((\d+:){2}\d{2})', fpath)]
        # Determine if we need to crop the clip at all
        secs_from_start = (start - clip_st).seconds if start > clip_st else 0
        secs_from_end = -1 * (clip_end - end).seconds if clip_end > end else None
        return secs_from_start, secs_from_end

    def make_clip_from_filenames(self, start_dt: dt, end_dt: dt, file_list: List[str],
                                 trim_files: bool = True, prefix: str = 'motion') -> str:
        """Takes in a list of file paths, determines the cropping necessary
        based on the timerange in the path and downloads the video clip to a temp filepath"""
        clips = []
        for dl_file in file_list:
            clip = VideoFileClip(dl_file)
            if trim_files:
                trim_st, trim_end = self._get_trim_range_from_filename(dl_file, start_dt, end_dt)
                clip = clip.subclip(trim_st, trim_end)
            clip = (clip.resize(self.resize_perc).speedx(self.speed_x))
            # Append to our clips
            clips.append(clip)
        final = concatenate_videoclips(clips, method='compose')
        fpath = os.path.join(self.temp_dir, f'{prefix}_{start_dt:%T}_to_{end_dt:%T}.mp4')
        final.write_videofile(fpath)
        return fpath

    def concat_files(self, filepath_list: List[str]) -> str:
        """Concatenates a list of mp4 filepaths into one & saves it"""
        clips = []
        for filepath in filepath_list:
            clip = VideoFileClip(filepath)
            clips.append(clip)
        final = concatenate_videoclips(clips, method='compose')
        final_fpath = os.path.join(self.temp_dir, 'motion_concatenated_file.mp4')
        final.write_videofile(final_fpath)
        return final_fpath

    def draw_on_motion(self, fpath: str, min_area: int = 500, min_frames: int = 10,
                       threshold: int = 25) -> Tuple[bool, Optional[str]]:
        """Draws rectangles around motion items and re-saves the file
            If True is returned, the file has some motion highlighted in it, otherwise it doesn't have any

        Args:
            fpath: the path to the mp4 file
            min_area: the minimum contour area (pixels)
            min_frames: the threshold of frames the final file must have. Fewer than this will return False
            threshold: min threshold (out of 255). used when calculating img differences

        NB! threshold probably shouldn't exceed 254
        """
        # Read in file
        vs = cv2.VideoCapture(fpath)
        vs.set(3, self.vid_w)
        vs.set(4, self.vid_h)
        fframe = None
        nth_frame = 0
        frames = []
        prev_contours = []
        while True:
            # Grab the current frame
            ret, frame = vs.read()
            if frame is None:
                # If frame could not be grabbed, we've likely reached the end of the file
                break
            # Resize the frame, convert to grayscale, blur it
            try:
                frame = imutils.resize(frame, width=self.vid_w)
                gray = self._grayscale_frame(frame)
            except AttributeError:
                continue

            # If the first frame is None, initialize it
            if fframe is None:
                fframe = gray
                continue
            rects, contours, cframe = self._detect_contours(
                fframe, frame, min_area, threshold, unique_only=False
            )
            if rects > 0:
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if nth_frame % 100 == 0:
                print(f'Frame {nth_frame} reached.')
            nth_frame += 1

        vs.release()
        if len(frames) > min_frames:
            # Rewrite the output file with moviepy
            #   Otherwise Slack won't be able to play the mp4 due to h264 codec issues
            return True, self.write_frames(frames, fpath)
        return False, None

    def write_frames(self, frames: List[np.ndarray], filepath: str) -> str:
        """Writes the frames to a given .mp4 filepath (h264 codec)"""
        vclip = ImageSequenceClip(frames, fps=self.fps)
        vclip.write_videofile(filepath, codec='libx264', fps=self.fps)
        return filepath

    @staticmethod
    def _grayscale_frame(frame: np.ndarray, blur_lvl: int = 21) -> np.ndarray:
        """Converts a frame to grayscale"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (blur_lvl, blur_lvl), 0)
        return gray

    def _detect_contours(self, first_frame: np.ndarray, cur_frame: np.ndarray,
                         min_area: int = 500, threshold: int = 25, contour_lim: int = 10,
                         prev_contours: List[np.ndarray] = None, unique_only: bool = False) -> \
            Tuple[int, List[np.ndarray], np.ndarray]:
        """Methodology used to detect contours in image differences

        Args:
            first_frame: the frame to use as base comparison
            cur_frame: the frame to compare for changes
            min_area: the minimum (pixel?) area of changes to be flagged as a significant change
            threshold: seems like the gradient of the change (in grayscale?) to identify changes?
            contour_lim: integer-wise means of detecting changes in contours (larger => more different)
            prev_contours: List of previous contours (used for detecting unique contours
            unique_only: if True, will perform unique contour analysis
        """
        # Compute absolute difference between current frame and first frame
        gray = self._grayscale_frame(cur_frame)
        fdelta = cv2.absdiff(first_frame, gray)
        thresh = cv2.threshold(fdelta, threshold, 255, cv2.THRESH_BINARY)[1]
        # Dilate the thresholded image to fill in holes, then find contours
        #   on thresholded image
        thresh = cv2.dilate(thresh, None, iterations=2)
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        # Capture unique contours
        unique_cnts = prev_contours.copy() if prev_contours is not None else []

        # Loop over contours
        rects = 0
        for cnt in cnts:
            # Ignore contour if it's too small
            if cv2.contourArea(cnt) < min_area:
                continue
            if unique_only:
                # Check for unique contours
                if any([cv2.matchShapes(cnt, ucnt, 1, 0.0) > contour_lim for ucnt in unique_cnts]):
                    # Unique contour - add to group
                    # Otherwise compute the bounding box for the contour & draw it on the frame
                    (x, y, w, h) = cv2.boundingRect(cnt)
                    cv2.rectangle(cur_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    unique_cnts.append(cnt)
                    rects += 1
            else:
                # Just pick up any contours
                (x, y, w, h) = cv2.boundingRect(cnt)
                cv2.rectangle(cur_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                rects += 1

        return rects, unique_cnts, cv2.cvtColor(cur_frame, cv2.COLOR_BGR2RGB)


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
