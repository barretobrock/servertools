from servertools import OpenWRT, SlackComm
from kavalkilu import Hosts, Log


logg = Log('ba-connected')
h = Hosts()
ow = OpenWRT()
sc = SlackComm()

ow.save_connections_file()
