#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Determines if mobile is connected to local network. If not, will arm the cameras"""
import os
from kavalkilu import Amcrest, Keys, Log, LogArgParser, Hosts, MySQLLocal


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('cam_active', log_lvl=LogArgParser().loglvl)

cred = Keys().get_key('webcam_api')
# Get only cameras without numbers in the name
cam_info_list = Hosts().get_hosts(r'(?!^ac-.*\d.*$)^ac-.+$')
eng = MySQLLocal('homeautodb')


def arm_camera(cam_dict, arm):
    """Toggles motion detection on/off"""
    try:
        cam = Amcrest(cam_dict['ip'], cred, name=cam_dict['name'])
        # Toggle motion
        cam.toggle_motion(set_motion=arm)
        # Set PTZ to 'armed' area
        cam.set_ptz_flag(armed=arm)
        # Get PTZ xyz coordinates
        return cam.get_current_ptz_coordinates()
    except Exception as e:
        log.error('Unexpected exception occurred: {}'.format(e))


res_list = []
# Check if mobile(s) are connected to LAN
for ip in [i['ip'] for i in Hosts().get_hosts('an-[bm]a.*')]:
    resp = os.system('ping -c 1 {}'.format(ip))
    res_list.append(True if resp == 0 else False)

# If anyone home, don't arm, otherwise arm
arm_cameras = not any(res_list)
for cam_dict in cam_info_list:
    if not arm_cameras:
        log.debug('One of the devices are currently in the network. Disabling motion detection.')
    ptz_coords = arm_camera(cam_dict, arm_cameras)
    update_query = """
            UPDATE
                cameras
            SET
                is_armed = {} 
                , is_connected = TRUE 
                , ptz_loc = '{}'
                , update_date = NOW()
                , last_check_date = NOW()
            WHERE
                ip = '{}'

        """.format(arm_cameras, ptz_coords, cam_dict['ip'])
    # Update values in db
    eng.write_sql(update_query)

log.close()
