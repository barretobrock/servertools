from typing import List, Dict
from kavalkilu import HOME_SERVER_HOSTNAME


class HostnameNotFoundException(Exception):
    pass


class IPAddressNotFoundException(Exception):
    pass


class ServerHosts:
    """Everything associated with the Hosts API"""
    def __init__(self):
        # Definitions of the prefixes stored in the hostnames
        self.prefix_dict = {
            HOME_SERVER_HOSTNAME: 'server',
            'lt': 'laptop',
            'pi': 'raspberry pi',
            'ac': 'camera',
            're': 'camera',
            'an': 'mobile',
            'ot': 'misc'
        }
        self.all_hosts = []
        # Populate the hosts list for the first time
        self.read_hosts()

    def read_hosts(self):
        """Reads in /etc/hosts, parses data"""
        with open('/etc/hosts', 'r') as f:
            hostlines = f.readlines()
        hostlines = [line.strip().split(' ') for line in hostlines if line.startswith('192.168')]
        hosts = []
        for ip, name in hostlines:
            try:
                prefix = name.strip().split('-')[0]
                mach_type = self.prefix_dict[prefix]
            except KeyError:
                mach_type = 'unknown'

            hosts.append({
                'ip': ip.strip(),
                'name': name.strip(),
                'machine_type': mach_type
            })
        self.all_hosts = hosts

    def reload(self):
        """Reloads the hosts"""
        self.read_hosts()

    def get_all_names(self) -> List[str]:
        """Returns a list of all the """
        return [x['name'] for x in self.all_hosts]

    def get_all_ips(self) -> List[str]:
        """Returns a list of all the """
        return [x['ip'] for x in self.all_hosts]

    def get_host(self, ip: str) -> Dict[str, str]:
        """Returns ip from host name"""
        for host in self.all_hosts:
            if host['ip'] == ip:
                return host
        raise HostnameNotFoundException(f'Hostname not found for ip {ip}.')

    def get_ip(self, hostname: str) -> Dict[str, str]:
        """Returns ip from host name"""
        for host in self.all_hosts:
            if host['name'] == hostname:
                return host
        raise IPAddressNotFoundException(f'IP address not found for hostname {hostname}.')
