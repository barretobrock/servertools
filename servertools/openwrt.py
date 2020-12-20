import os
import json
import socket
from datetime import datetime as dt
from typing import Tuple, List, Optional
from openwrt_luci_rpc import OpenWrtRpc
from kavalkilu import Keys


class OpenWRT(OpenWrtRpc):
    """Common methods for interacting with an OpenWRT router"""
    def __init__(self):
        super().__init__('192.168.1.1', *self._get_creds())
        self.data_path = os.path.join(os.path.expanduser('~'), *['data', 'connected-ips.json'])
        self.current_connections = self.get_active_connections()
        self.previous_connections = self.get_previously_active_connections()
        self._add_connection_time_to_new_clients()

    @staticmethod
    def _get_creds() -> Tuple[str, str]:
        """Collects the credentials"""
        creds = Keys().get_key('hidden-openwrt')
        return creds['un'], creds['pw']

    def get_active_connections(self) -> dict:
        """Collects active connections"""
        result = self.get_all_connected_devices(only_reachable=True)
        dev_dict = {}
        for device in result:
            ip = device.ip
            if ip.startswith('192.168'):
                dev_dict[ip] = {
                    'hostname': device.hostname,
                    'mac': device.mac
                }
        return dev_dict

    def _add_connection_time_to_new_clients(self):
        """Adds a 'since' key to ips that have recently connected"""
        for ip in self.current_connections.keys():
            if self.check_ip_changed_connection(ip) == 'CONNECTED':
                # Connected between now and the last time this report was run
                self.current_connections[ip]['since'] = dt.now().strftime('%F %T')

    def get_previously_active_connections(self):
        """Collects from a saved file of previously connected devices"""
        if os.path.exists(self.data_path):
            # Read in the previous dictionary of connected ips
            with open(self.data_path) as f:
                prev_dev_dict = json.loads(f.read())
            return prev_dev_dict
        return {}

    def save_connections_file(self):
        """Saves the dictionary of current connections to the connections file"""
        with open(self.data_path, 'w') as f:
            json.dump(self.current_connections, f)

    def check_ip_changed_connection(self, ip: str) -> str:
        """Checks if a given ip changed connection status recently
        returns:
            DISCONNECTED, CONNECTED, NO CHANGE
        """
        if ip in self.current_connections.keys() and ip not in self.previous_connections.keys():
            # Recently connected
            return 'CONNECTED'
        elif ip not in self.current_connections.keys() and ip in self.previous_connections.keys():
            # Recently connected
            return 'DISCONNECTED'
        return 'NO CHANGE'

    def check_ip_connected(self, ip: str) -> bool:
        """Checks if an IP address is currently connected"""
        return ip in self.current_connections.keys()

    def show_unknown_ips(self) -> List[str]:
        """Returns a list of ips that are currently connected and not statically assigned"""
        unknown_ips = []
        for ip in self.current_connections.keys():
            if int(ip.split('.')[-1]) >= 100:
                unknown_ips.append(ip)
        return unknown_ips

    def collect_ip_info(self, ip: str, port_range: Optional[Tuple[int, int]] = (1, 1000)) -> Optional[dict]:
        """Returns info on device with given ip by scanning it"""
        if ip not in self.current_connections.keys():
            return None
        hostname = self.current_connections[ip]['hostname']
        mac = self.current_connections[ip]['mac']

        result_dict = {'ip': ip, 'hostname': hostname, 'mac': mac}
        if port_range is not None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            open_ports = []
            for port in range(*port_range):
                try:
                    result = sock.connect_ex((ip, port))
                except socket.gaierror:
                    # Hostname could not be resolved
                    break
                if result == 0:
                    open_ports.append(port)
            result_dict['open_ports'] = open_ports
        return result_dict
