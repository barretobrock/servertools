#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Determines if mobile is connected to local network. When connections change, will post to channel"""
import os
import pandas as pd
from kavalkilu import Log, LogArgParser, NetTools, Hosts
from kavalkilu.local_tools import slack_comm, user_marelle, alert_channel, wifi_channel


# Initiate Log, including a suffix to the log name to denote which instance of log is running
log = Log('machine_conn', log_lvl=LogArgParser().loglvl)
today = pd.datetime.now()

fpath = os.path.join(os.path.abspath(Paths().data_dir), 'machine_connected.json')

# Get connections of all the device we want to track
machines = Hosts().get_hosts(regex=r'^(an).*')
machines_df = pd.DataFrame(machines)

# Read in the json file if there is one
if os.path.exists(fpath):
    cur_state_df = pd.read_json(fpath)
else:
    cur_state_df = machines_df.copy()
    for col in ['status', 'update_date', 'connected_since']:
        cur_state_df[col] = None

cur_state_df = cur_state_df.rename(columns={'status': 'prev_status'})
# Merge with machines_df
machines_df = machines_df.merge(cur_state_df, how='left', on=['name', 'ip'])

for i, row in machines_df.iterrows():
    # Ping machine
    machine_name = row['name']
    prev_status = row['prev_status']
    status = NetTools(ip=row['ip']).ping(5)
    log.debug(f'Ping result for {machine_name}: {status}')
    machines_df.loc[i, 'status'] = status
    if pd.isnull(prev_status):
        # Log new machine regardless of current status
        log.info(f'New machine logged: {machine_name}')
        slack_msg = f'A new machine `{machine_name}` will be loaded into `logdb.devices`.'
        slack_comm.send_message(wifi_channel, slack_msg)
        machines_df.loc[i, 'update_date'] = today
        machines_df.loc[i, 'connected_since'] = today
    else:
        if status != prev_status:
            # State change
            log.info('Machine changed state: {}'.format(machine_name))
            slack_msg = f'`{machine_name}` changed state from `{prev_status}` to `{status}`. ' \
                        f'Record made in `logdb.devices`.'
            slack_comm.send_message(alert_channel, slack_msg)
            machines_df.loc[i, 'update_date'] = today

# Notify on specific device state changes
for devname in ['an-barret']:
    df = machines_df.loc[machines_df.name == devname]
    prev_status = df['prev_status'].values[0]
    status = df['status'].values[0]
    if not pd.isnull(prev_status):
        if prev_status != status:
            if status == 'CONNECTED':
                msg = f'<@{user_marelle}> Mehe ühik on taas koduvõrgus! :meow_party:'
            else:
                msg = 'Mehe ühik on koduvõrgust läinud :sadcowblob:'
            slack_comm.send_message(wifi_channel, msg)


# Enforce column order
machines_df = machines_df[['name', 'ip', 'status', 'update_date', 'connected_since']]

# Save to JSON
machines_df.to_json(fpath)

log.close()
