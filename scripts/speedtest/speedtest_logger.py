#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from speedtest import Speedtest
import pandas as pd
from kavalkilu.tools import Log, LogArgParser, Paths, MySQLLocal


p = Paths()
logg = Log('speedtest.logger', 'speedtest', log_lvl=LogArgParser().loglvl)


# Prep speedtest by getting nearby servers
speed = Speedtest()
servers = speed.get_servers([])
best_server = speed.get_best_server()

down = speed.download()/1000000
up = speed.upload()/1000000
ping = best_server['latency'] if 'latency' in best_server.keys() else None

# put variables into pandas type dataframe
test = pd.DataFrame({
    'test_date': pd.datetime.now(),
    'download': down,
    'upload': up,
    'ping': ping
}, index=[0])

data_cols = ['download', 'upload', 'ping']
test.loc[:, data_cols] = test[data_cols].applymap(lambda x: round(float(x), 4))

# Connect to db
eng = MySQLLocal('speedtestdb')

# Write dataframe to db
eng.write_dataframe('speedtest', test)

logg.close()
