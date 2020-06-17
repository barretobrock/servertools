#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sends messages to Slack"""
from slacktools import SlackTools
from kavalkilu import Keys


class SlackComm:
    def __init__(self):
        vcreds = Keys().get_key('viktor_creds')
        self.st = SlackTools(**vcreds)
        self.alert_channel = 'alerts'
        self.notify_channel = 'notifications'
        self.wifi_channel = 'wifi-pinger-dinger'
        self.log_channel = 'logs'
        self.user_me = 'UM35HE6R5'
        self.user_marelle = 'UM3E3G72S'
