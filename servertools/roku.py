#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from roku import Roku
from.hosts import ServerHosts


class RokuTV(Roku):
    """
    Customized functions for use with Roku TV
    """

    # Popular app ids
    NETFLIX = 12
    YOUTUBE = 837
    CHROMECAST = 'tvinput.hdmi1'
    PRIME = 13
    GOOGLE_PLAY = 50025

    # Popular Shows

    def __init__(self, roku_ip=None):
        # Set path to roku TV ip
        h = ServerHosts()
        if roku_ip is None:
            roku_ip = h.get_ip('ot-roku')
        self.tv = Roku.__init__(self, roku_ip)

    def power(self):
        """Toggles power to TV"""
        self.tv._post('/keypress/Power')

    def mute(self):
        """Mutes TV"""
        self.tv._post('/keypress/VolumeMute')

    def volume_up(self):
        self.tv._post('/keypress/VolumeUp')

    def volume_down(self):
        self.tv._post('/keypress/VolumeDown')

    def go_home(self):
        """Navigate back home"""
        self.tv.home()

    def goto_app(self, app_name):
        """Navigates to designated app"""
        app = self.tv['app_name']
        app.launch()
        # Things to do to get past load screens and get to search
        if app_name == self.NETFLIX:
            self.tv.select()
            self.tv.left()
            self.tv.up()
            self.tv.select()

    def goto_show(self, app_name, show_name):
        """Navigates to show page in app"""
        # Go to the app
        self.goto_app(app_name)
        # Method to navigate to search area
        if app_name == self.NETFLIX:
            self.tv.left()
            self.tv.up()
            self.tv.select()
        elif app_name == self.PRIME:
            self.tv.left()
            self.tv.select()
        # Search for the show
        self.tv.literal(show_name)
        # Pick the first result, of course
        if app_name == self.NETFLIX:
            self.tv.right()
            self.tv.right()
            self.tv.select()
            self.tv.select()
