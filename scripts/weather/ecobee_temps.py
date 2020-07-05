#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Method to collect temperature and other useful data from ecobee"""
from datetime import datetime, timedelta
from kavalkilu import Log
from servertools import EcoBee


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('ecobee_temp', log_dir='weather', log_to_db=True)
eco = EcoBee()

temp_now = datetime.now()
temp_10m_ago = (temp_now - timedelta(minutes=10))
data = eco.collect_data(temp_10m_ago, temp_now)


log.debug('Temp logging successfully completed.')

log.close()
