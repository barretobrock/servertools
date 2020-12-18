import requests
from kavalkilu import Hosts


class HAHelper:
    """Wrapper for Home Assistant methods"""
    PORT = 8123

    def __init__(self):
        self.ip = Hosts().get_ip_from_host('homeassistant')
        self.base_url = f'http://{self.ip}:{self.PORT}'
        self.webhook_url = f'{self.base_url}/api/webhook'

    def call_webhook(self, path: str):
        """Sends a call to an automation with a webhook trigger"""
        resp = requests.post(f'{self.webhook_url}/{path}')
