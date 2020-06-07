#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Determines if mobile is connected to local network. If not, will arm the cameras"""
import paho.mqtt.publish as publish
from servertools import Amcrest, OpenWRT
from kavalkilu import Log, Hosts


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('cam_active')
ow = OpenWRT()
hosts = Hosts()
# Get only cameras without numbers in the name
cam_info_list = hosts.get_hosts_and_ips(r'(?!^ac-.*\d.*$)^ac-.+$')

res_list = []
currently_active_ips = ow.get_active_connections()
# Check if mobile(s) are connected to LAN
for ip in [i['ip'] for i in hosts.get_hosts_and_ips('an-[bm]a.*')]:
    res_list.append(ip in currently_active_ips.keys())

# If anyone home, don't arm, otherwise arm
arm_cameras = not any(res_list)
arm_status = 'ARMED' if arm_cameras else 'UNARMED'
if not arm_cameras:
    log.debug('One of the devices are currently in the network. Disabling motion detection.')
else:
    log.debug('None of the devices are currently in the network. Enabling motion detection.')
for cam_dict in cam_info_list:
    cam = Amcrest(cam_dict['ip'])
    if cam.camera_type != 'doorbell':
        cam.arm_camera(arm_cameras)
        publish.single(f'sensors/cameras/{cam.name}/status', arm_status, hostname='homeserv.local')

log.close()
