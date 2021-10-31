#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from roku import Roku, Application
from typing import Optional
from kavalkilu import Hosts


class RokuTV(Roku):
    """
    Customized functions for use with Roku TV
    """

    # Popular app names
    NETFLIX = 'Netflix'
    YOUTUBE = 'YouTube'
    CHROMECAST = 'Chromecast'
    PRIME = 'Prime Video'
    GOOGLE_PLAY = 'Google Play Movies & TV'

    def __init__(self, roku_ip: str = None):
        # Set path to roku TV ip
        h = Hosts()
        if roku_ip is None:
            roku_ip = h.get_ip_from_host('ot-roku')
        super().__init__(roku_ip)

    def power(self):
        """Toggles power to TV"""
        self._post('/keypress/Power')

    def mute(self):
        """Mutes TV"""
        self._post('/keypress/VolumeMute')

    def volume_up(self):
        self._post('/keypress/VolumeUp')

    def volume_down(self):
        self._post('/keypress/VolumeDown')

    def go_home(self):
        """Navigate back home"""
        self.home()

    def get_app_by_name(self, name: str) -> Optional[Application]:
        """Get a Roku App by Application name"""
        for app in self.apps:
            if app.name.lower() == name.lower():
                return app
        return None

    def goto_app(self, name: str):
        """Navigates to designated app"""
        app = self.get_app_by_name(name)
        if app is None:
            raise ValueError(f'App name "{name}" not found')
        app.launch()
        # Things to do to get past load screens and get to search
        if app.name == self.NETFLIX:
            self.select()
            self.left()
            self.up()
            self.select()

    def goto_show(self, app_name: str, show_name: str):
        """Navigates to show page in app"""
        # Go to the app
        self.goto_app(app_name)
        # Method to navigate to search area
        if app_name == self.NETFLIX:
            self.left()
            self.up()
            self.select()
        elif app_name == self.PRIME:
            self.left()
            self.select()
        # Search for the show
        self.literal(show_name)
        # Pick the first result, of course
        if app_name == self.NETFLIX:
            self.right()
            self.right()
            self.select()
            self.select()
