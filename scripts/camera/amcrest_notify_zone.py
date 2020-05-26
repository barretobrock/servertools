#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Determines if mobile is connected to local network. If not, will arm the cameras"""
import os
from servertools import Amcrest
from kavalkilu import Keys, Log, LogArgParser, Hosts, MQTTClient


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('cam_active', log_lvl=LogArgParser().loglvl)
mqtt = MQTTClient('homeserv')
cred = Keys().get_key('webcam_api')
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


res_list = []
# Check if mobile(s) are connected to LAN
for ip in [i['ip'] for i in Hosts().get_hosts('an-[bm]a.*')]:
    resp = os.system('ping -c 1 {}'.format(ip))
    res_list.append(True if resp == 0 else False)

# If anyone home, don't arm, otherwise arm
arm_cameras = not any(res_list)
arm_status = 'ARMED' if arm_cameras else 'UNARMED'
for cam_dict in cam_info_list:
    if not arm_cameras:
        log.debug('One of the devices are currently in the network. Disabling motion detection.')
    cam_name = cam_dict['name']
    if 'doorbell' not in cam_name:
        arm_camera(cam_dict, arm_cameras)
        mqtt.publish(f'sensors/cameras/{cam_name.replace("ac-", "")}/status', arm_status)

mqtt.disconnect()
log.close()
