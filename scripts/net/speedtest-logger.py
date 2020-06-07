#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Performs a speedtest assessment"""
import paho.mqtt.publish as publish
from speedtest import Speedtest
from datetime import datetime as dt
import pandas as pd
from kavalkilu import Log


logg = Log('speedtest')
# Prep speedtest by getting nearby servers
logg.debug('Instantiating speedtest object.')
speed = Speedtest()
servers = speed.get_servers([])
best_server = speed.get_best_server()

logg.debug('Server selected. Beginning speed test.')
down = speed.download()/1000000
up = speed.upload()/1000000
ping = best_server['latency'] if 'latency' in best_server.keys() else None
logg.debug(f'Returned down: {down:.1f} up: {up:.1f} ping: {ping:.1f}')

# put variables into pandas type dataframe
test = pd.DataFrame({
    'test_date': dt.now(),
    'download': down,
    'upload': up,
    'ping': ping
}, index=[0])

data_cols = ['download', 'upload', 'ping']
test.loc[:, data_cols] = test[data_cols].applymap(lambda x: round(float(x), 4))

for col in data_cols:
    data = test[col].values[0]
    publish.single(f'sensors/net/speed/{col}', data, hostname='homeserv.local')

logg.close()
