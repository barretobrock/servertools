#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sends messages to Slack"""
from slacktools import SlackTools
from kavalkilu import Keys


class SlackComm:
    def __init__(self):
        get_key = Keys().get_key
        # self.grafana_creds = get_key('grafana-api')
        team = get_key('okr-name')
        xoxp = get_key('kodubot-usertoken')
        xoxb = get_key('kodubot-useraccess')

        self.st = SlackTools(team, xoxp_token=xoxp, xoxb_token=xoxb)
        self.alert_channel = 'alerts'
        self.notify_channel = 'notifications'
        self.wifi_channel = 'wifi-pinger-dinger'
        self.log_channel = 'logs'
        self.user_me = 'UM35HE6R5'
        self.user_marelle = 'UM3E3G72S'
