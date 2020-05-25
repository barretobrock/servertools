#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Method to collect temperature and other useful data from ecobee"""
from kavalkilu import OpenHab, Log, LogArgParser, MySQLLocal
from datetime import datetime


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('ecobee_temp', log_dir='temps', log_lvl=LogArgParser().loglvl)

# Initiate Openhab
oh = OpenHab()
LOC_ID = 3
VAL_TBLS = ['temps', 'humidity']


def log_values(loc_id, ts, measurement_list, tbl_list, conn, log=log):
    """
    Logs measurements to the database. If measurements are None-type, fails gracefully.
    Args:
        loc_id: int, the location id
        ts: str, ISO-format timestamp
        measurement_list: list of floats, the measurements to record
        tbl_list: list of str, the tables to insert into. NOTE: Must be of equal length to measurement_list
        conn: database connection
        log: logger
    """

    if len(measurement_list) != len(tbl_list):
        raise ValueError("List size mismatch: measurement_list and tbl_list sizes aren't equal!")

    # Build a dictionary of the values we're moving around
    insert_list = [
        {
            'loc_id': loc_id,
            'record_date': ts,
            'record_value': x,
            'tbl': y
        } for x, y in zip(measurement_list, tbl_list)
    ]

    for d in insert_list:
        if d['record_value'] is None:
            # If no record value, don't go through with inserting into table
            log.error('No record value found. Not recording to table "{tbl}"'.format(**d))
        else:
            # For humidity and temp, insert into tables
            insert_query = """
                INSERT INTO {tbl} (`loc_id`, `record_date`, `record_value`)
                VALUES ({loc_id}, "{record_date}", {record_value})
            """.format(**d)
            insert_log = conn.execute(insert_query)
            log.debug('Query sent to table "{tbl}". Result shows {0} rows affected.'.format(insert_log.rowcount, **d))


temp_dict = oh.read_value('Temp_Upstairs')
hum_dict = oh.read_value('Hum_Upstairs')

ha_db = MySQLLocal('homeautodb')
conn = ha_db.engine.connect()

temp_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
temp_avg = round(float(temp_dict['state']), 2)
hum_avg = round(float(hum_dict['state']), 2)

# Log the values into the tabl
log_values(LOC_ID, temp_time, [temp_avg, hum_avg], VAL_TBLS, conn)

conn.close()

log.debug('Temp logging successfully completed.')

log.close()
