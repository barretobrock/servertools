#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from random import random, randint, uniform
from phue import Bridge, Light, Sensor
from typing import Union, Tuple, List, Optional
from kavalkilu import Hosts


class HueBridge(Bridge):
    """Commands for Philips Hue Bridge"""
    def __init__(self, bridge_ip: str = None):
        """
        Args:
            bridge_ip: str, ip address to the Philips Hue bridge.
                default is resolved from ip
        """
        # Set path to bridge ip

        h = Hosts()
        if bridge_ip is None:
            bridge_ip = h.get_ip_from_host('ot-huehub')
        super().__init__(bridge_ip)
        # Bridge button may need to be pressed the first time this is used
        self.connect()
        self.api = self.get_api()


class HueBulb(Light):
    """Commands for Philips Hue bulbs"""
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
    #B-S-H-COL
    SCENE_WARM_FULL = (FULL_BRIGHTNESS, 166, 9728, (0.4447, 0.3968))
    SCENE_WARM_DIM = (6, 166, 9728, (0.5019, 0.4152))

    def __init__(self, light_id: str, bridge_ip: str = None):
        """
        Args:
            light_id: str name of light to control
            bridge_ip: str, ip address to the Philips Hue bridge
        """
        self.bridge = HueBridge(bridge_ip)
        # Initialize the light object
        super().__init__(self.bridge, light_id)
        self.is_color_bulb = 'color' in self.type
        # Set previous color for when we need to transition back to an original color
        self.previous_color = None

    def turn_on(self):
        """Turns light on"""
        self.on = True

    def turn_off(self):
        """Turns light off"""
        self.on = False

    def toggle(self):
        """Toggles light"""
        if self.get_status():
            # On
            self.turn_off()
        else:
            self.turn_on()
            if self.brightness < 10:
                # Make sure they're at the default brightness
                self.set_brightness(self.FULL_BRIGHTNESS)

    def get_status(self) -> bool:
        """Determine if light is on/off"""
        return self.on

    def blink(self, times: int, wait: float = 0.5, trans_time: float = 0.1, bright_pct: float = 1,
              color: Tuple[float] = None):
        """Blinks light x times, waiting y seconds between"""
        # Set what mode light is currently in
        cur_mode = self.get_status()
        prev_color = None
        if color is not None:
            prev_color = self.previous_color
            self.set_color(color)
        default_trans_time = self.get_transition_time()
        # Set new transition time
        self.set_transition_time(trans_time)
        for x in range(0, times):
            self.turn_on()
            self.set_brightness(self.FULL_BRIGHTNESS * bright_pct)
            time.sleep(wait / 2)
            self.turn_off()
            time.sleep(wait / 2)
        # Return to default transition time
        self.set_transition_time(default_trans_time)
        if color is not None:
            self.set_color(prev_color)
        if cur_mode:
            # Turn light back on if it was previously on
            self.turn_on()

    def set_brightness(self, level: float):
        """Set brightness to x%
        Args:
            level: float, the brightness level to set
        """
        if level < 1:
            # Set level to percentage
            level = int(level * self.FULL_BRIGHTNESS)
        elif level > self.FULL_BRIGHTNESS:
            level = self.FULL_BRIGHTNESS

        self.brightness = level

    def set_saturation(self, level: float):
        """
        Set saturation level (lower number gets closer to white)
        Args:
            level: int, saturation level
        """
        if self.is_color_bulb:
            if level < 1:
                # Set level to a percentage
                level = int(level * self.FULL_SATURATION)
            elif level > self.FULL_SATURATION:
                level = self.FULL_SATURATION

            self.saturation = level

    def set_hue(self, level: float):
        """Set hue level of light"""
        if self.is_color_bulb:
            self.hue = level

    def set_bshcol(self, brightness: float, saturation: float, hue: float, color: Tuple[float]):
        """Sets brightness saturation hue and color all at once"""
        self.set_brightness(brightness)
        self.set_saturation(saturation)
        self.set_hue(hue)
        self.set_color(color)

    def set_color(self, color_coord: Union[Tuple[float], List[float]]):
        """Set the color of the light with x,y coordinates (0-1)"""
        if self.is_color_bulb:
            self.previous_color = self.xy
            self.xy = color_coord

    def get_color(self) -> List[float]:
        """Gets the xy color coordinates"""
        if self.is_color_bulb:
            return self.xy

    def set_rand_color(self):
        """Sets random color"""
        self.set_color([random(), random()])

    def do_alert(self, single: bool = True, flash_secs: int = 10, color: List[float] = None):
        """Puts light into alert mode (flashing)"""
        if color is not None:
            # Set the bulb color before the alert
            self.set_color(color)
        if single:
            self.alert = 'select'
        else:
            self.alert = 'lselect'
            end_time = time.time() + flash_secs
            while end_time > time.time():
                pass
                time.sleep(0.1)
            # Turn off flashing
            self.alert = 'none'
        if color is not None:
            self.set_color(self.previous_color)

    def get_transition_time(self) -> float:
        """Gets the transition time of the bulb on/off"""
        return self.transitiontime

    def set_transition_time(self, time_s: Union[int, float] = None):
        """Sets the transition time of the bulb on/off"""
        self.transitiontime = time_s

    def candle_mode(self, duration_s: int):
        """Turn HueBulb into a candle"""

        end_time = time.time() + duration_s

        while end_time > time.time():
            self.set_hue(randint(5000, 10500))
            self.set_saturation(randint(150, 255))
            self.set_brightness(randint(50, 255))
            self.set_transition_time(randint(1, 3))
            time.sleep(uniform(0.5, 3) / 10)


class HueSensor(Sensor):
    """Commands for Philips Hue Sensors"""
    # These are properties that get set on instantiation but are hidden from inspection due to __setattr__
    on = None
    battery = None

    def __init__(self, name: str, bridge_ip: str = None):
        self.bridge = HueBridge(bridge_ip)
        super().__init__(self.bridge, name)
        self.id = self.bridge.get_sensor_id_by_name(self.name)
        # Load all config items as attributes
        self._refresh_config_items()

    def _get_sensor_config_item(self, item: str) -> Optional[str]:
        """Retrieves the item stored in the sensor's config"""
        return self.config.get(item)

    def _set_sensor_config_item(self, item: str, value: Union[str, float, bool]):
        """Sets the sensor by communicating sensor changes with the bridge.
        These changes then get populated 'back' to the sensor automatically
        """
        self.bridge.set_sensor_config(self.id, item, value)
        self._refresh_config_items()

    def _refresh_config_items(self):
        """Refresh all the config items"""
        for k, v in self.config.items():
            self.__setattr__(k, v)

    def turn_on(self):
        """Turn the sensor on"""
        self._set_sensor_config_item('on', True)

    def turn_off(self):
        """Turn the sensor off"""
        self._set_sensor_config_item('on', False)

    def toggle(self):
        """Toggle the sensor"""
        self._set_sensor_config_item('on', not self.on)
