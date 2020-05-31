"""Currently tracks when my phone has recently changed connection state with the LAN"""
from servertools import OpenWRT, SlackComm
from kavalkilu import Hosts, Log


logg = Log('ba-connected')
h = Hosts()
ow = OpenWRT()
sc = SlackComm()

ips = h.get_hosts(r'an-barret')
for ip_dict in ips:
    ip = ip_dict['ip']
    if ow.check_ip_changed_connection(ip) == 'CONNECTED':
        # IP recently connected
        sc.st.send_message(sc.wifi_channel,
                           f'<@{sc.user_marelle}> Mehe ühik on taas koduvõrgus!:peanuts:')
    if ow.check_ip_changed_connection(ip) == 'DISCONNECTED':
        # IP recently disconnected
        sc.st.send_message(sc.wifi_channel,
                           f'Mehe ühik on koduvõrgust läinud :sadcowblob:')
