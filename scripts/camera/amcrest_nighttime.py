#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Activates nighttime mode on cameras"""
from kavalkilu import (
    Hosts,
    LogWithInflux,
)

from servertools import Amcrest

# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = LogWithInflux('cam_night')
hosts = Hosts()
# Get only cameras without numbers in the name
cam_info_list = hosts.get_hosts_and_ips(r'^ac-(ga|el)')


for cam_dict in cam_info_list:
    # Instantiate cam & arm
    cam = Amcrest(cam_dict['ip'])
    if cam.camera_type != 'doorbell':
        cam.arm_camera(True)
        # publish.single(f'sensors/cameras/{cam.name}/status', 'ARMED', hostname='tinyserv.local')

log.close()
