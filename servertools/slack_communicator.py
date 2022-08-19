#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sends messages to Slack"""
from loguru._logger import Logger
from pukr import get_logger
from slacktools import (
    BlockKitBuilder,
    SecretStore,
    SlackTools,
)


class SlackComm:
    def __init__(self, bot: str = 'sasha', parent_log: Logger = None):
        credstore = SecretStore('secretprops.kdbx')
        bot_creds = credstore.get_key_and_make_ns(bot)
        if parent_log is None:
            self.log = get_logger(self.__class__.__name__)
        else:
            self.log = parent_log.bind(child_name=self.__class__.__name__)
        self.st = SlackTools(bot_cred_entry=bot_creds, parent_log=self.log, use_session=False)
        self.bkb = BlockKitBuilder()
        if bot == 'sasha':
            # Channels
            self.hoiatuste_kanal = 'hoiatused'
            self.ilma_kanal = 'ilm'
            self.kodu_kanal = 'kodu'
            self.kaamerate_kanal = 'kaamerad'
            self.meemide_kanal = 'meemid'
            self.teatede_kanal = 'teated'
            self.test_kanal = 'test'
            self.koduv6rgu_kanal = 'koduvõrk'
            # Users
            self.user_me = 'U015WMFQ0DV'
            self.user_marelle = 'U016N5RJZ9C'
        elif bot == 'viktor':
            # Users
            self.user_me = 'UM35HE6R5'
            self.user_marelle = 'UM3E3G72S'
