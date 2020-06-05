import amcrest
import requests
import re
from requests.auth import HTTPDigestAuth
from requests.exceptions import ConnectionError
from typing import Optional
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
        self.config_url = f'http://{ip}/cgi-bin/configManager.cgi?action=setConfig'
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
