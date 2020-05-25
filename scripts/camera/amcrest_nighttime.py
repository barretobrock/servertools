#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Activates nighttime mode on cameras"""
from kavalkilu import Keys, Log, LogArgParser, Hosts, Amcrest, MySQLLocal


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('cam_night', log_lvl=LogArgParser().loglvl)
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


for cam_dict in cam_info_list:
    # Instantiate cam & arm
    ptz_coords = arm_camera(cam_dict, True)

    update_query = """
        UPDATE
            cameras
        SET
            is_armed = TRUE 
            , is_connected = TRUE 
            , ptz_loc = '{}'
            , update_date = NOW()
            , last_check_date = NOW()
        WHERE
            ip = '{}'
    
    """.format(ptz_coords, cam_dict['ip'])
    # Update values in db
    eng.write_sql(update_query)

log.close()
