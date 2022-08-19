#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

from .camera import (
    Amcrest,
    Reolink,
)
from .gif import (
    GIF,
    GIFSlice,
    GIFTile,
)
from .gsheets import GSheetReader
from .light import (
    HueBridge,
    HueBulb,
    HueSensor,
)
from .message import Email
from .openwrt import OpenWRT
from .plants import (
    Plant,
    Plants,
)
from .roku import RokuTV
from .selenium import (
    BrowserAction,
    ChromeDriver,
)
from .slack_communicator import SlackComm
from .text import (
    MarkovModel,
    TextCleaner,
    TextHelper,
    XPathExtractor,
)
from .video import VidTools
from .weather import (
    NWSAlert,
    NWSAlertZone,
    NWSForecast,
    NWSForecastZone,
    OpenWeather,
    OWMLocation,
    SlackWeatherNotification,
    YRNOLocation,
    YrNoWeather,
)

__version__ = '2.0.0'
__update_date__ = '2022-04-23_10:56:59'
ROOT_DIR = Path(__file__).parents[1]
LOG_DIR = Path().home().joinpath('logs')
