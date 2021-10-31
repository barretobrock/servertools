#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from .camera import Amcrest, Reolink
from .gsheets import GSheetReader
from .gif import GIF, GIFSlice, GIFTile
from .light import HueBulb, HueSensor, HueBridge
from .message import Email
from .openwrt import OpenWRT
from .roku import RokuTV
from .selenium import ChromeDriver, BrowserAction
from .slack_communicator import SlackComm
from .text import MarkovModel, XPathExtractor, TextCleaner, TextHelper
from .video import VidTools
from .weather import OpenWeather, OWMLocation, YrNoWeather, YRNOLocation, \
    NWSAlert, NWSAlertZone, SlackWeatherNotification, NWSForecast, NWSForecastZone


from ._version import get_versions
__version__ = get_versions()['version']
__update_date__ = get_versions()['date']
del get_versions
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
