#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from flask import Flask, request, redirect
from flask_jsonpify import jsonify
from servertools import ServerHosts, Secrets, get_secret_file

app = Flask(__name__)

shost = ServerHosts()

# Get password for secrets database
password = get_secret_file('SECRETPROP')
secrets = Secrets(password)


@app.route('/hosts', methods=['GET'])
def hosts():
    """Simple GET all hosts with static IPs"""
    host_name = request.args.get('name', default=None, type=str)
    ip = request.args.get('ip', default=None, type=str)
    if host_name is not None:
        result = [shost.get_ip(host_name)]
    elif ip is not None:
        result = [shost.get_host(ip)]
    else:
        # Get everything
        result = shost.hosts
    return jsonify({'data': result})


@app.route('/reload', methods=['GET'])
def reload():
    secrets.load_database(password)
    return redirect('/keys')


@app.route('/key/<key_name>', methods=['GET'])
def key(key_name: str):
    entry = secrets.get_entry(key_name)
    if entry is None:
        return {}
    resp = {
        'un': entry.username,
        'pw': entry.password
    }
    resp.update(entry.custom_properties)
    if len(entry.attachments) > 0:
        for att in entry.attachments:
            # For attachments, try to decode any that we might expect. For now, that's just JSON
            if isinstance(att.data, bytes):
                # Decode to string, try loading as json
                resp[att.filename] = json.loads(att.data.decode('utf-8'))
    return jsonify({'data': [resp]})


@app.route('/keys', methods=['GET'])
def keys():
    """Simple GET all keys with static IPs"""
    # Get all available keys
    all_keys = secrets.db.entries
    results = sorted([f'{x.path} (m:{x.mtime.astimezone()})' for x in all_keys])
    return jsonify({'data': results})


if __name__ == '__main__':
    secret_key = get_secret_file('FLASK_SECRET')
    app.secret_key = secret_key
    app.run(host='0.0.0.0', port='5002')
