# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """Performs a speedtest assessment"""
# from datetime import datetime as dt
# import sys
#
# from kavalkilu import (
#     InfluxDBHomeAuto,
#     InfluxDBLocal,
#     LogWithInflux,
# )
# import pandas as pd
# from speedtest import (
#     Speedtest,
#     SpeedtestBestServerFailure,
# )
#
# logg = LogWithInflux('speedtest')
# influx = InfluxDBLocal(InfluxDBHomeAuto.NETSPEED)
# # Prep speedtest by getting nearby servers
# logg.debug('Instantiating speedtest object.')
# speed = Speedtest()
# servers = speed.get_servers([])
# server = None
# for attempt in range(3):
#     logg.debug(f'Best server get attempt {attempt + 1}...')
#     try:
#         server = speed.get_best_server()
#         break
#     except Exception as e:
#         logg.warning(f'Best server get failed. Exception: {e}')
#
# if server is None:
#     logg.warning('No suitable speedtest server was found... Exiting script early.')
#     sys.exit(1)
#
# logg.debug('Server selected. Beginning speed test.')
# down = speed.download()/1000000
# up = speed.upload()/1000000
# ping = server['latency'] if 'latency' in server.keys() else None
# logg.debug(f'Returned down: {down:.1f} up: {up:.1f} ping: {ping:.1f}')
#
# # put variables into pandas type dataframe
# test = pd.DataFrame({
#     'test_date': dt.now(),
#     'download': down,
#     'upload': up,
#     'ping': ping
# }, index=[0])
#
# data_cols = ['download', 'upload', 'ping']
# test.loc[:, data_cols] = test[data_cols].applymap(lambda x: round(float(x), 4))
# # Add server details
# test['server'] = f'{server["sponsor"]} ({server["name"]})'
#
# # Feed into Influx
# influx.write_df_to_table(test, 'server', ['download', 'upload', 'ping'], 'test_date')
# influx.close()
#
# logg.close()
