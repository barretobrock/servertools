#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
from flask import Flask
from flask_jsonpify import jsonify

app = Flask(__name__)


@app.route('/hosts', methods=['GET'])
def hosts():
    """Simple GET all hosts with static IPs"""
    with open('/etc/hosts', 'r') as f:
        hostlines = f.readlines()
    hostlines = [line.strip().split(' ') for line in hostlines if line.startswith('192.168.0')]
    hosts = [{'ip': ip, 'name': name} for ip, name in hostlines]
    result = {'data': hosts}
    return jsonify(result)


@app.route('/keys', methods=['GET'])
def keys():
    """Simple GET all keys with static IPs"""

    key_dir = os.path.join(os.path.expanduser('~'), 'keys')

    key_list = []
    # Iterate through list of files in directory
    for dirpath, dirnames, filenames in os.walk(key_dir):
        for file in filenames:
            filepath = os.path.join(dirpath, file)
            if os.path.isfile(filepath):
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
    result = {'data': key_list}
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5002')
