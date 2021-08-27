"""Tracks all currently connected machines, notifies of IPs that
    haven't been statically assigned"""
import pandas as pd
from slacktools import BlockKitBuilder
from servertools import OpenWRT, SlackComm
from kavalkilu import Hosts, LogWithInflux, InfluxDBLocal, InfluxDBHomeAuto


logg = LogWithInflux('machine-conn')
h = Hosts()
ow = OpenWRT()

# Log active IPs
device_df = pd.concat([pd.DataFrame(data=vals, index=[ip]) for ip, vals in ow.current_connections.items()])
# Drop the mac address
device_df = device_df.reset_index().rename(columns={'index': 'ip'})
# Add a dummy value column
device_df['up'] = 1
# Push to influx
influx = InfluxDBLocal(InfluxDBHomeAuto.MACHINES)
influx.write_df_to_table(device_df, ['ip', 'hostname'], 'up')
influx.close()

# Unknown IP scan
logg.debug('Beginning scan of unknown ips.')
unknown_ips = ow.show_unknown_ips()
logg.debug(f'Found {len(unknown_ips)} unknown ips.')
if len(unknown_ips) > 0:
    bkb = BlockKitBuilder()
    sc = SlackComm(parent_log=logg)
    blocks = []
    msg_chunk = []
    for ip in unknown_ips:
        if ow.check_ip_changed_connection(ip) == 'CONNECTED':
            # Unknown ip recently connected. Notify
            # Collect info on the ip; don't scan ports
            logg.debug(f'IP {ip} recently connected. Notifying channel.')
            ip_info_dict = ow.collect_ip_info(ip, None)
            msg_chunk.append('`{ip}`:\t\t{hostname}\t\t{mac}'.format(**ip_info_dict))
    if len(msg_chunk) > 0:
        blocks = [
            bkb.make_context_section('Unknown IP(s) recently connected.'),
            bkb.make_block_divider(),
            bkb.make_block_section(msg_chunk)
        ]
        sc.st.send_message(sc.koduv6rgu_kanal, message='Unknown IP message', blocks=blocks)

# This basically just replaces the file of saved ips that are currently connected to the router
logg.debug('Saving current connection states.')
ow.save_connections_file()
logg.close()
