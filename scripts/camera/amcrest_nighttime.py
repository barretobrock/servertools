#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Activates nighttime mode on cameras"""
import paho.mqtt.publish as publish
from servertools import Amcrest
from kavalkilu import Log, Hosts


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('cam_night')
hosts = Hosts()
# Get only cameras without numbers in the name
cam_info_list = hosts.get_hosts_and_ips(r'(?!^ac-.*\d.*$)^ac-.+$')


for cam_dict in cam_info_list:
    # Instantiate cam & arm
    cam = Amcrest(cam_dict['ip'])
    if cam.camera_type != 'doorbell':
        cam.arm_camera(True)
        publish.single(f'sensors/cameras/{cam.name}/status', 'ARMED', hostname='homeserv.local')

log.close()
