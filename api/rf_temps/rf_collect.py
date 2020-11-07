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
from kavalkilu import InfluxDBLocal, InfluxDBNames, InfluxTblNames, Log, GracefulKiller


logg = Log('rf_temp')
UDP_IP = "192.168.1.5"
UDP_PORT = 1433

# device id to device-specific data mapping
mappings = {
    9459: {
        'name': 'freezer'
    },
    6853: {
        'name': 'kontor-wc'
    },
    210: {
        'name': 'neighbor-porch'
    },
    14539: {
        'name': 'fridge'
    },
    5252: {
        'name': 'elutuba'
    },
    12476: {
        'name': 'suur-wc'
    },
    8416: {
        'name': 'alumine-r6du'
    }
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
influx = InfluxDBLocal(InfluxDBNames.HOMEAUTO)
killer = GracefulKiller()

# Set up methods to periodically send processed data packets to Influx
interval = datetime.now()
split_s = 600   # Data packet to influx interval
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
        logg.error_with_class(e, 'Unable to parse this object. Skipping.')
        continue

    if "model" not in data:
        # Exclude anything that doesn't contain a device 'model' key
        continue

    # Begin processing the data
    if data is not None:
        # Begin extraction process
        if data['id'] in mappings.keys():
            # Device is known... record data
            measurements = {}
            for k, v in possible_measurements.items():
                if k in data.keys():
                    measurements[v] = data[k]
            if len(measurements) > 0:
                # Write to dataframe
                measurements.update({
                    'location': mappings[data['id']]['name'],
                    'timestamp': data['time']
                })
                data_df = data_df.append(pd.DataFrame(measurements, index=[0]))
                logg.debug('Successfully recorded object to dataframe..')
        else:
            logg.info(f'Unknown device found: {data["model"]}: ({data["id"]})')

    if (datetime.now() - interval).total_seconds() > split_s:
        # Gone over the time limit. Try to log all the non-duplicate info to database
        data_df = data_df.drop_duplicates()
        # Enforce data types
        for col in ['temp', 'humidity']:
            if col in data_df.columns:
                data_df[col] = data_df[col].astype(float)
        logg.debug(f'Logging interval reached. Sending over {data_df.shape[0]} points to db.')
        influx.write_df_to_table(InfluxTblNames.TEMPS, data_df, tags='location',
                                 value_cols=['temp', 'humidity'], time_col='timestamp')
        # Reset our info
        logg.debug('Resetting interval and dataframe.')
        interval = datetime.now()
        data_df = pd.DataFrame()

logg.debug('Collection ended. Closing Influx connection')
influx.close()
logg.close()
