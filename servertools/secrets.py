import os
from typing import Dict
from pykeepass import PyKeePass
from pykeepass.entry import Entry
from kavalkilu import Path


p = Path()
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


def get_secret_file(fname: str) -> str:
    """Grabs a file containing a 'metasecret' (secret for obtaining secrets)"""
    secret_path = p.easy_joiner(p.keys_dir, fname)
    if not p.exists(secret_path):
        raise FileNotFoundError(f'File at \'{secret_path}\' does not exist.')
    with open(secret_path) as f:
        return f.read().strip()


def read_props() -> Dict[str, str]:
    props = {}
    with open(os.path.join(ROOT_DIR, 'secretprops.properties'), 'r') as f:
        contents = f.read().split('\n')
        for item in contents:
            if item != '':
                key, value = item.split('=', 1)
                props[key] = value.strip()
    return props


class Secrets:
    DATABASE_PATH = p.easy_joiner(p.keys_dir, 'secretprops.kdbx')

    def __init__(self, password: str):
        self.db = None
        # Read in the database
        self.load_database(password)

    def load_database(self, password: str):
        self.db = PyKeePass(self.DATABASE_PATH, password=password)

    def get_entry(self, entry_name: str) -> Entry:
        return self.db.find_entries(title=entry_name, first=True)
