#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Posts error logs to #errors channel in Slack"""
import os
import pandas as pd
from kavalkilu import MySQLLocal, Log, LogArgParser, Paths
from kavalkilu.local_tools import slack_comm, log_channel


log = Log('slack_logger', log_lvl=LogArgParser().loglvl)
db = MySQLLocal('logdb')
mysqlconn = db.engine.connect()
datapath = os.path.join(Paths().data_dir, 'slack_logs.txt')


def save_log_tbl(df, fpath=datapath):
    """Saves logs to path"""
    with open(fpath, 'w') as f:
        f.write(slack_comm.df_to_slack_table(df))


log_splitter = {
    'normal': {
        'channel': '#logs',
        'levels': ['DEBUG', 'INFO']
    },
    'error': {
        'channel': '#logs',
        'levels': ['ERROR', 'WARN']
    }
}

# We read errors from x hours previous
hour_interval = 4
now = pd.datetime.now()
# The date to measure from
read_from = (now - pd.Timedelta(hours=hour_interval)).replace(minute=0, second=0)

error_logs_query = """
    SELECT 
        machine_name AS machine
        , log_name AS log
        , time AS log_ts
        , level AS lvl
        , exc_class
        , exc_msg
    FROM 
        logs
    WHERE
        time >= '{:%F %T}'
    ORDER BY 
        time ASC 
""".format(read_from)
result_df = pd.read_sql_query(error_logs_query, mysqlconn)

msg = "`{:%H:%M}` to `{:%H:%M}`:\n".format(read_from, now)
if not result_df.empty:
    result_df['cnt'] = 1
    result_df = result_df.groupby(['machine', 'log', 'lvl', 'exc_class', 'exc_msg',
                                   pd.Grouper(key='log_ts', freq='H')]).count().reset_index()
    # Establish column order
    result_df = result_df[['log_ts', 'machine', 'log', 'lvl', 'exc_class', 'exc_msg', 'cnt']]
    for log_type, log_dict in log_splitter.items():
        channel = log_dict['channel']
        df = result_df[result_df.lvl.isin(log_dict['levels'])].copy()
        if df.shape[0] > 0:
            df['log_ts'] = pd.to_datetime(df['log_ts']).dt.strftime('%d %b %H:%M')
            df.loc['total'] = df.copy().sum(numeric_only=True)
            df['cnt'] = df['cnt'].astype(int)
            df = df.fillna('')
            if log_type == 'normal':
                # remove the exception-related columns
                df = df.drop(['exc_class', 'exc_msg'], axis=1)
        msg += '\t\t{}: {}\n'.format(log_type, df.shape[0])
else:
    msg += 'No logs.'
# Send the info to Slack
slack_comm.send_message(log_channel, msg)



