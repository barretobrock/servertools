#!/usr/bin/env python3
"""
ETL for RTL_433 json objects via syslog -> processed Dataframe -> influx

Note: depends on `rf_stream` already being running and feeding data to port 1433
    via `rtl_433 -F syslog::1433`
"""
import json
from json import JSONDecodeError
import socket
from datetime import datetime
import pandas as pd
from kavalkilu import InfluxDBLocal, InfluxDBHomeAuto, LogWithInflux, \
    GracefulKiller, Hosts, HOME_SERVER_HOSTNAME, HAHelper
from servertools import SlackComm


logg = LogWithInflux('rf_temp', log_dir='rf')
sc = SlackComm(parent_log=logg)
UDP_IP = Hosts().get_ip_from_host(HOME_SERVER_HOSTNAME)
UDP_PORT = 1433

# device id to device-specific data mapping
mappings = {
    3092: {'name': 'magamistuba'},
    5252: {'name': 'elutuba'},
    6853: {'name': 'kontor-wc'},
    8416: {'name': 'r6du-l22ne'},
    9459: {'name': 'freezer'},
    9533: {'name': 'kontor'},
    10246: {'name': 'v2lisuks'},
    12476: {'name': 'suur-wc'},
    14539: {'name': 'fridge'},
    15227: {'name': 'r6du-ida'}
}
# Other items that aren't sensors
other_mappings = {

}

# Map the names of the variables from the various sensors to what's acceptable in the db
possible_measurements = {
    'temperature_C': 'temp',
    'humidity': 'humidity'
}


def parse_syslog(ln: bytes) -> str:
    """Try to extract the payload from a syslog line."""
    ln = ln.decode("ascii")  # also UTF-8 if BOM
    if ln.startswith("<"):
        # fields should be "<PRI>VER", timestamp, hostname, command, pid, mid, sdata, payload
        fields = ln.split(None, 7)
        ln = fields[-1]
    return ln


logg.debug('Establishing socket...')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.bind((UDP_IP, UDP_PORT))

logg.debug('Connecting to Influx..')
influx = InfluxDBLocal(InfluxDBHomeAuto.TEMPS)
killer = GracefulKiller()

# Set up methods to periodically send processed data packets to Influx
interval = datetime.now()
# Adjust interval to be an even 10 mins
replace_mins = interval.minute - interval.minute % 10
interval = interval.replace(minute=replace_mins, second=0, microsecond=0)
split_s = 300   # Data packet to influx interval
logg.debug(f'Data packets sent to Influx every {split_s / 60} mins.')
data_df = pd.DataFrame()

logg.debug('Beginning loop!')
while not killer.kill_now:
    line, _addr = sock.recvfrom(1024)
    # Convert line from bytes to str, prep for conversion into dict
    line = parse_syslog(line)
    data = None
    try:
        data = json.loads(line)
        # logg.debug(f'Seeing: {data}')
    except JSONDecodeError as e:
        logg.error_from_class(e, 'Unable to parse this object. Skipping.')
        continue

    if "model" not in data:
        # Exclude anything that doesn't contain a device 'model' key
        continue

    # Begin processing the data
    if data is not None:
        # Begin extraction process
        dev_id = data.get('id')
        dev_model = data.get('model')
        logg.debug(f'Receiving from device: {dev_model} ({dev_id})')
        if dev_id in mappings.keys():
            loc = mappings[dev_id]['name']
            logg.debug(f'Device identified. Location: {loc}')
            # Device is known sensor... record data
            measurements = {}
            for k, v in possible_measurements.items():
                if k in data.keys():
                    measurements[v] = data[k]
            if len(measurements) > 0:
                # Write to dataframe
                measurements.update({
                    'location': loc,
                    'timestamp': data['time']
                })
                data_df = data_df.append(pd.DataFrame(measurements, index=[0]))
                logg.debug('Successfully recorded object to dataframe..')
        elif dev_id in other_mappings.keys():
            pass
            # Handle signal another way
            # item = other_mappings.get(data['id']).get('name')
            # if item == 'gdo':
            #     # Routines for notifying gdo was used
            #     sc.st.send_message(sc.kodu_kanal, 'Someone used the garage door remote!')
            # elif item == 'doorbell':
            #     # Routines for notifying doorbell was used
            #     HAHelper().call_webhook('doorbell_pressed')
        else:
            logg.info(f'Unknown device found: {dev_model}: ({dev_id})\n'
                      f'{json.dumps(data, indent=2)}')

    if (datetime.now() - interval).total_seconds() > split_s:
        # Gone over the time limit. Try to log all the non-duplicate info to database
        data_df = data_df.drop_duplicates()
        # Enforce data types
        for col in ['temp', 'humidity']:
            if col in data_df.columns:
                data_df[col] = data_df[col].astype(float)
        logg.debug(f'Logging interval reached. Sending {data_df.shape[0]} data points to db.')
        influx.write_df_to_table(data_df, tags='location', value_cols=['temp', 'humidity'], time_col='timestamp')
        # Reset our info
        logg.debug('Resetting interval and dataframe.')
        interval = datetime.now()
        data_df = pd.DataFrame()

logg.debug('Collection ended. Closing Influx connection')
influx.close()
logg.close()
