from typing import List
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
            'an': 'mobile',
            'ot': 'misc'
        }
        self.hosts = self.read_hosts()

    def read_hosts(self) -> List[dict]:
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

        return hosts

    def get_all_names(self) -> List[str]:
        """Returns a list of all the """
        return [x['name'] for x in self.hosts]

    def get_all_ips(self) -> List[str]:
        """Returns a list of all the """
        return [x['ip'] for x in self.hosts]

    def get_host(self, ip: str) -> str:
        """Returns ip from host name"""
        for host in self.hosts:
            if host['ip'] == ip:
                return host['name']
        raise HostnameNotFoundException(f'Hostname not found for ip {ip}.')

    def get_ip(self, hostname: str) -> str:
        """Returns ip from host name"""
        for host in self.hosts:
            if host['name'] == hostname:
                return host['ip']
        raise HostnameNotFoundException(f'IP address not found for hostname {hostname}.')
