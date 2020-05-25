#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
from typing import Union


class Domoticz:
    """
    Send and receive data from a computer running Domoticz Home Automation server
    Args for __init__:
        server: local IP of server running Domoticz master
        port: Domoticz connection port. default=8080
    """
    def __init__(self, server: str, port: int = 8080):
        self.server = server
        self.port = port
        self.prefix_url = f'http://{self.server}:{self.port}/json.htm?type=command'
        self.curl_type = 'Accept: application/json'

    def _send_command(self, cmd_url: str):
        """Send the command to the server via cURL"""
        subprocess.check_call(['curl', '-s', '-i', '-H', self.curl_type, cmd_url])

    def _switch_cmd(self, device_id: Union[int, str], cmd: str, is_group: bool = False) -> str:
        """Builds the url to send to the server"""
        switch_type = 'scene' if is_group else 'light'
        return f'{self.prefix_url}&param=switch{switch_type}&idx={device_id}&switchcmd={cmd}'

    def switch_on(self, device_id: Union[int, str]):
        """Sends an 'on' command to a given switch's id"""
        url = self._switch_cmd(device_id, 'On', is_group=False)
        self._send_command(url)

    def switch_off(self, device_id: Union[int, str]):
        """Sends an 'off' command to a given switch's id"""
        url = self._switch_cmd(device_id, 'Off', is_group=False)
        self._send_command(url)

    def toggle_switch(self, device_id: Union[int, str]):
        """Toggle a given switch between 'on' and 'off'"""
        url = self._switch_cmd(device_id, 'Toggle', is_group=False)
        self._send_command(url)

    def send_sensor_data(self, device_id: Union[int, str], value: float):
        """
        Send data collected from a certain sensor
        Args:
            device_id: int, id of the given device
            value: float, measurement made by the given sensor
        """
        url = f'{self.prefix_url}&param=udevice&idx={device_id}&nvalue=0&svalue={value}'
        self._send_command(url)

    def switch_group_off(self, group_id: Union[int, str]):
        """Switches off a group based on its id"""
        url = self._switch_cmd(group_id, 'Off', is_group=True)
        self._send_command(url)

    def switch_group_on(self, group_id):
        """Switches on a group based on its id"""
        url = self._switch_cmd(group_id, 'On', is_group=True)
        self._send_command(url)
