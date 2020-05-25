#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sends messages to Slack"""
from slacktools import SlackTools
from ..tools.net import Keys


get_key = Keys().get_key
creds = get_key('grafana-api')
team = get_key('okr-name')
xoxp = get_key('kodubot-usertoken')
xoxb = get_key('kodubot-useraccess')

slack_comm = SlackTools(team, xoxp_token=xoxp, xoxb_token=xoxb)
alert_channel = 'alerts'
notify_channel = 'notifications'
wifi_channel = 'wifi-pinger-dinger'
log_channel = 'logs'
user_me = 'UM35HE6R5'
user_marelle = 'UM3E3G72S'
