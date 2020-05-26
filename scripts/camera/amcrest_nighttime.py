#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Activates nighttime mode on cameras"""
from servertools import Amcrest
from kavalkilu import Keys, Log, LogArgParser, Hosts, MQTTClient


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('cam_night', log_lvl=LogArgParser().loglvl)
cred = Keys().get_key('webcam_api')
mqtt = MQTTClient('homeserv')
# Get only cameras without numbers in the name
cam_info_list = Hosts().get_hosts(r'(?!^ac-.*\d.*$)^ac-.+$')


def arm_camera(cam_dict: dict, arm: bool):
    """Toggles motion detection on/off"""
    try:
        cam = Amcrest(cam_dict['ip'], cred, name=cam_dict['name'])
        # Toggle motion
        cam.toggle_motion(set_motion=arm)
        # Set PTZ to 'armed' area
        cam.set_ptz_flag(armed=arm)
    except Exception as e:
        log.error('Unexpected exception occurred: {}'.format(e))


for cam_dict in cam_info_list:
    # Instantiate cam & arm
    cam_name = cam_dict['name']
    if 'doorbell' not in cam_name:
        arm_camera(cam_dict, True)
        mqtt.publish(f'sensors/cameras/{cam_name.replace("ac-", "")}/status', 'ARMED')

mqtt.disconnect()
log.close()
