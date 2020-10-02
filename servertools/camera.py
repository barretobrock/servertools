import amcrest
import requests
import re
import os
import cv2
import imutils
import tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageSequenceClip
from datetime import datetime as dt, timedelta
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError
from typing import Optional, List, Dict, Tuple
from kavalkilu import Keys


class GIFTools:
    """Class for handling GIFs"""
    pass


class VidTools:
    """Class for general video editing"""
    temp_dir = tempfile.gettempdir()
    temp_mp4_in_fpath = os.path.join(temp_dir, 'tempin.mp4')
    temp_mp4_out_fpath = os.path.join(temp_dir, 'tempout.mp4')
    resize_perc = 0.5
    speed_x = 6

    def __init__(self, vid_w: int = 640, vid_h: int = 360, resize_perc: float = None, speed_x: int = None):
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
                                 trim_files: bool = True):
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
        final = concatenate_videoclips(clips)
        final.write_videofile(self.temp_mp4_in_fpath)

    def draw_on_motion(self, min_area: int = 500, threshold: int = 25) -> bool:
        """Draws rectangles around motion items and re-saves the file
            If True is returned, the file has some motion highlighted in it, otherwise it doesn't have any

        Args:
              min_area: the minimum contour area (pixels)
              threshold: min threshold (out of 255). used when calculating img differences

        NB! threshhold probably shouldn't exceed 254
        """
        # Read in file
        vs = cv2.VideoCapture(self.temp_mp4_in_fpath)
        vs.set(3, self.vid_w)
        vs.set(4, self.vid_w)
        fframe = None
        frames = []
        while True:
            # Grab the current frame
            ret, frame = vs.read()
            if frame is None:
                # If frame could not be grabbed, we've likely reached the end of the file
                break
            # Resize the frame, convert to grayscale, blur it
            try:
                frame = imutils.resize(frame, width=self.vid_w)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)
            except AttributeError:
                continue

            # If the first frame is None, initialize it
            if fframe is None:
                fframe = gray
                continue

            # Compute absolute difference between current frame and first frame
            fdelta = cv2.absdiff(fframe, gray)
            thresh = cv2.threshold(fdelta, threshold, 255, cv2.THRESH_BINARY)[1]
            # Dilate the thresholded image to fill in holes, then find contours
            #   on thresholded image
            thresh = cv2.dilate(thresh, None, iterations=2)
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = imutils.grab_contours(cnts)

            # Loop over contours
            rects = 0
            for cnt in cnts:
                # Ignore contour if it's too small
                if cv2.contourArea(cnt) < min_area:
                    continue

                # Otherwise compute the bounding box for the contour & draw it on the frame
                (x, y, w, h) = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                rects += 1
            if rects > 0:
                # If a contour was drawn, write the frame to file
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        vs.release()
        if len(frames) > 0:
            # Rewrite the output file with moviepy
            #   Otherwise Slack won't be able to play the mp4 due to h264 codec issues
            vclip = ImageSequenceClip(frames, fps=20)
            vclip.write_videofile(self.temp_mp4_out_fpath, codec='libx264', fps=20)
            return True
        return False


for log in motion_logs:
    start = log['start'] - timedelta(seconds=10)
    end = log['end'] + timedelta(seconds=10)
    dl_files = self.cam.download_files_from_range(start, end, self.temp_dir)
    # clips = self.cam.make_clip_from_filename(start, end, dl_files)
    # clip = concatenate_videoclips(clips)
    # Write concatenated clip to temp file
    # clip.write_videofile(self.temp_inmp4_fpath)
    # vs = cv2.VideoCapture(self.temp_inmp4_fpath)
    # vid_w = 640
    # vid_h = 360
    # vs.set(3, vid_w)
    # vs.set(4, vid_h)
    # Might need to do the following for this to work
    #   sudo apt install ffmpeg x264 libx264-dev
    # initialize first frame in video stream

    # TODO: If tot_frames > 0, send signal that file is worth uploading, otherwise don't
    #   Maybe some files have false positives
    # gif_path = self.cam.get_gif_for_range(log['start'], log['end'])
    # self.sc.st.upload_file('kaamerad', gif_path, os.path.split(gif_path)[1])


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
    def _consolidate_events(events: List[Dict[str, dt]], limit_s: int = 60) -> Optional[List[Dict[str, dt]]]:
        """Takes in a list of motion events and consolidates them if they're within range of each other"""
        new_events = []
        prev_event_end = None
        event_start = None
        if len(events) == 0:
            return []
        event = None
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

    def download_files_from_range(self, start_dt: dt, end_dt: dt,
                                  temp_dir: str) -> List[str]:
        """Downloads mp4 files from a set datetime range"""
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
        return dl_files



    def get_gif_for_range(self, start_dt: dt, end_dt: dt, buffer_s: int = 30, resize_perc: float = 0.5,
                          speed_x: int = 6) -> str:
        """For a given range, retrieves the video (mp4) and converts to gif.
        Returns the path to the saved gif"""
        # TODO: test that a range sub the 5min interval retrieves a single mp4 file
        temp_dir = tempfile.gettempdir()
        start_dt = start_dt - timedelta(seconds=buffer_s)
        end_dt = end_dt + timedelta(seconds=buffer_s)
        # Pull the files associated with the timerange provided
        dl_files = self.download_files_from_range(start_dt, end_dt, temp_dir)

        # Now go through the downloaded files and combine them
        clips = self.make_clip_from_filename(start_dt, end_dt, dl_files, resize_perc, speed_x)
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
