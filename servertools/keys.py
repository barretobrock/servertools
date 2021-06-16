import os
import json
from typing import List, Union


class ServerKeys:
    def __init__(self):
        self.key_dir = os.path.join(os.path.expanduser('~'), 'keys')
        self.keys = self.load_keys()

    def load_keys(self) -> List[dict]:
        """Collect all stored keys"""

        fileext_deny_list = ['.kdbx']
        key_list = []
        # Iterate through list of files in directory
        for dirpath, dirnames, filenames in os.walk(self.key_dir):
            for file in filenames:
                filepath = os.path.join(dirpath, file)
                fileext = os.path.splitext(filepath)[-1]
                if os.path.isfile(filepath) and 'hidden' not in file and fileext not in fileext_deny_list:
                    with open(filepath, 'r') as f:
                        txt = f.read()
                        try:
                            creds = json.loads(txt)
                        except json.JSONDecodeError:
                            # File was not in JSON format (possibly no brackets or double quotes)
                            creds = txt.replace('\n', '')
                    # Separate file name from extension
                    fname = os.path.splitext(file)[0]
                    key_list.append({'name': fname, 'keys': creds})
        return key_list

    def get_all_key_names(self) -> List[str]:
        """Get all the key names"""
        return [x['name'] for x in self.keys]

    def get_keys(self, name: str) -> List[dict]:
        """Gets specific key by name"""
        return [x for x in self.keys if x['name'] == name]

    def get_key(self, name: str) -> Union[List[dict], str]:
        """Gets specific key by name"""
        for item in self.keys:
            if item['name'] == name:
                keys = item['keys']
                if isinstance(keys, str):
                    # Remove extra whitespace if returning only string
                    return keys.strip()
                else:
                    return item['keys']
