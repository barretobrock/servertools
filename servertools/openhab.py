#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .path import Paths
import requests
import datetime


class OpenHab:
    """
    Placeholder for OpenHab-type actions
    """
    p = Paths()

    def __init__(self, oh_ip=p.openhab_ip, port=8080):
        """
        Args:
            oh_ip: str, ip address of openhab
            port: int, port number to openhab default=8080
        """
        self.addr_prefix = 'http://{}:{}'.format(oh_ip, port)
        self.item_url = '{}/rest/items/'.format(self.addr_prefix)

    def update_value(self, item_name, data):
        """
        Updates Openhab item with given value
        Args:
            item_name: str, name of the item in Openhab
            data: str int or float, data to send
        """
        if isinstance(data, str):
            data = str(data).encode('utf-8')
        elif isinstance(data, datetime.datetime):
            # Convert to a timestamp str
            data = data.strftime('%Y-%m-%dT%H:%M:%S')

        self.whole_url = '{}{}'.format(self.item_url, item_name)
        openhab_response = requests.post(self.whole_url, data=data,
                                         allow_redirects=True, headers={'Connection': 'close'})

        return openhab_response

    def read_value(self, item_name, param_name='ALL'):
        """
        Reads in a value assigned
        Args:
            item_name: str, name of the item in OpenHab
            param_name: str, name of the item's parameter default: ALL
        """
        self.whole_url = '{}{}'.format(self.item_url, item_name)

        openhab_response = requests.get(self.whole_url, headers={'Connection': 'close'}).json()
        if param_name != 'ALL':
            return openhab_response[param_name]
        else:
            return openhab_response

