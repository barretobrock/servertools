"""Tracks all currently connected machines, notifies of IPs that
    haven't been statically assigned"""
from slacktools import BlockKitBuilder
from servertools import OpenWRT, SlackComm
from kavalkilu import Hosts, Log


logg = Log('ba-connected')
h = Hosts()
ow = OpenWRT()

unknown_ips = ow.show_unknown_ips()
if len(unknown_ips) > 0:
    bkb = BlockKitBuilder()
    sc = SlackComm()
    blocks = []
    msg_chunk = []
    for ip in unknown_ips:
        if ow.check_ip_changed_connection(ip) == 'CONNECTED':
            # Unknown ip recently connected. Notify
            # Collect info on the ip; don't scan ports
            ip_info_dict = ow.collect_ip_info(ip, None)
            msg_chunk.append('{ip}:\t\t{hostname}'.format(**ip_info_dict))
    if len(msg_chunk) > 0:
        blocks = [
            bkb.make_context_section('Unknown IP recently connected.'),
            bkb.make_block_divider(),
            bkb.make_block_section(msg_chunk)
        ]
        sc.st.send_message(sc.wifi_channel, message='', blocks=blocks)

# This basically just replaces the file of saved ips that are currently connected to the router
ow.save_connections_file()
