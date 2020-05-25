import amcrest
import requests
from requests.auth import HTTPDigestAuth
from typing import Optional


class Amcrest:
    """Amcrest camera-related methods"""
    def __init__(self, ip: str, creds: dict, port: int = 80, name: str = 'camera'):
        self.ip = ip
        self.name = name
        self.creds = creds
        self.config_url = f'http://{ip}/cgi-bin/configManager.cgi?action=setConfig'
        self.camera = amcrest.AmcrestCamera(ip, port, creds['user'], creds['password']).camera
        self.is_ptz_enabled = self._check_for_ptz()

    def _check_for_ptz(self) -> bool:
        """Checks if camera is capable of ptz actions"""
        return True if self.camera.ptz_presets_list() != '' else False

    def toggle_motion(self, set_motion: bool = True):
        """Sets motion detection"""
        motion_val = 'true' if set_motion else 'false'

        motion_url = f'{self.config_url}&MotionDetect[0].Enable={motion_val}'
        result = requests.get(motion_url, auth=HTTPDigestAuth(self.creds['user'], self.creds['password']))
        if result.status_code != 200:
            raise Exception('Error in HTTP GET response. Status code: '
                            f'{result.status_code}, Message: {result.text}')

    def set_ptz_flag(self, armed: bool):
        """Orients PTZ-enabled cameras either to armed position (1) or disarmed (2)"""

        if self.camera.ptz_presets_count > 0:
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
