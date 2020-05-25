#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read temperatures from several locations outside using Dallas sensors"""
from time import sleep
from kavalkilu import DallasTempSensor as Dallas, Log, LogArgParser, SensorLogger


log = Log('porch_temp', log_dir='temps', log_lvl=LogArgParser().loglvl)
# Serial numbers of the Dallas temp sensors
sensors = [
    {
        'sn': '28-0316b5f72bff',
        'loc': 'porch_upper_shade',
    }, {
        'sn': '28-0516a4a84eff',
        'loc': 'porch_upper_sun',
    }, {
        'sn': '28-0416c17b86ff',
        'loc': 'porch_lower_shade',
    }
]
sl_list = [SensorLogger(x['loc'], Dallas(x['sn'])) for x in sensors]

for slogger in sl_list:
    # Update every sensor's details
    slogger.update()
    sleep(1)

log.debug('Temp logging successfully completed.')

log.close()
