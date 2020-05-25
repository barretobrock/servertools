#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from random import random, randint, uniform
from phue import Bridge
from .hosts import ServerHosts


class HueBulb:
    """Commands for Philips Hue bulbs"""
    # Set path to bridge ip
    h = ServerHosts()
    b_ip = h.get_ip('ot-huehub')

    # Some interesting color coordinates
    DEFAULT = [0.4596, 0.4105]
    DEEP_RED = [0.9, 0.5]
    RED = [.6679, .3187]
    GREEN = [.085, .82]
    LIGHT_BLUE = [.15, .23]
    PURPLE = [.23, .05]
    PINK = [.4149, .1776]
    ORANGE = [.62, .37]
    YELLOW = [.52, .43]
    DEEP_BLUE = [.12, .03]
    FULL_BRIGHTNESS = 254
    FULL_SATURATION = 254

    def __init__(self, light_id, bridge_ip=b_ip):
        """
        Args:
            light_id: str name of light to control
            bridge_ip: str, ip address to the Philips Hue bridge
        """
        self.bridge = Bridge(bridge_ip)
        # Bridge button may need to be pressed the first time this is used
        self.bridge.connect()
        self.api = self.bridge.get_api()
        self.light_obj = self.bridge.get_light_objects('name')[light_id]

    def turn_on(self):
        """Turns light on"""
        self.light_obj.on = True

    def turn_off(self):
        """Turns light off"""
        self.light_obj.on = False

    def get_status(self):
        """Determine if light is on/off"""
        return self.light_obj.on

    def blink(self, times, wait=0.5, trans_time=0.1, bright_lvl=1):
        """Blinks light x times, waiting y seconds between"""
        # Set what mode light is currently in
        cur_mode = self.get_status()
        default_trans_time = self.transition_time()
        # Set new transition time
        self.transition_time(trans_time)
        for x in range(0, times):
            self.brightness(self.FULL_BRIGHTNESS * bright_lvl)
            self.turn_on()
            time.sleep(wait / 2)
            self.turn_off()
            time.sleep(wait / 2)
        # Return to default transition time
        self.transition_time(default_trans_time)
        if cur_mode:
            # Turn light back on if it was previously on
            self.turn_on()

    def brightness(self, level):
        """Set brightness to x%
        Args:
            level: float, the brightness level to set
        """
        if level < 1:
            # Set level to percentage
            level = int(level * self.FULL_BRIGHTNESS)

        self.light_obj.brightness = level

    def saturation(self, level):
        """
        Set saturation level (lower number gets closer to white)
        Args:
            level: int, saturation level
        """
        if level < 1:
            # Set level to a percentage
            level = int(level * self.FULL_SATURATION)

        self.light_obj.saturation = level

    def hue(self, level):
        """Set hue level of light"""
        self.light_obj.hue = level

    def color(self, color_coord):
        """Set the color of the light with x,y coordinates (0-1)"""
        self.light_obj.xy = color_coord

    def rand_color(self):
        """Sets random color"""
        self.color([random(), random()])

    def alert(self, single=True, flash_secs=10):
        """Puts light into alert mode (flashing)"""
        if single:
            self.light_obj.alert = 'select'
        else:
            self.light_obj.alert = 'lselect'
            end_time = time.time() + flash_secs
            while end_time > time.time():
                pass
                time.sleep(0.1)
            # Turn off flashing
            self.light_obj.alert = 'none'

    def transition_time(self, time_s=None):
        """Sets the transition time of the bulb on/off"""
        if time_s:
            self.light_obj.transitiontime = time_s
        else:
            return self.light_obj.transitiontime

    def candle_mode(self, duration_s):
        """Turn HueBulb into a candle"""

        end_time = time.time() + duration_s

        while end_time > time.time():
            self.hue(randint(5000, 10500))
            self.saturation(randint(150, 255))
            self.brightness(randint(50, 255))
            self.transition_time(randint(1, 3))
            time.sleep(uniform(0.5, 3) / 10)
