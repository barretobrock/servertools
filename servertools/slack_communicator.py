#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sends messages to Slack"""
from slacktools import SlackTools, BlockKitBuilder, SecretStore
from kavalkilu import LogWithInflux
from .secrets import read_props


class SlackComm:
    def __init__(self, bot: str = 'sasha', parent_log: LogWithInflux = None):
        creds = read_props()
        credstore = SecretStore('secretprops.kdbx', creds['secretprops_secret'])
        self.log = LogWithInflux(parent_log, child_name=self.__class__.__name__)
        self.st = SlackTools(credstore=credstore, parent_log=self.log, slack_cred_name=bot)
        self.bkb = BlockKitBuilder()
        if bot == 'sasha':
            self.hoiatuste_kanal = 'hoiatused'
            self.ilma_kanal = 'ilm'
            self.kodu_kanal = 'kodu'
            self.kaamerate_kanal = 'kaamerad'
            self.meemide_kanal = 'meemid'
            self.test_kanal = 'test'
            self.koduv6rgu_kanal = 'koduvõrk'
            self.user_me = 'U015WMFQ0DV'
            self.user_marelle = 'U016N5RJZ9C'
        elif bot == 'viktor':
            self.user_me = 'UM35HE6R5'
            self.user_marelle = 'UM3E3G72S'
