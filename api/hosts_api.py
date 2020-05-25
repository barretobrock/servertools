#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, request
from flask_jsonpify import jsonify
from servertools import ServerHosts, ServerKeys

app = Flask(__name__)
shost = ServerHosts()
skey = ServerKeys()


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


@app.route('/keys', methods=['GET'])
def keys():
    """Simple GET all keys with static IPs"""
    key_name = request.args.get('name', default=None, type=str)
    names_only = request.args.get('names_only', default=None, type=str)
    if key_name is not None:
        result = skey.get_key(key_name)
    elif names_only is not None:
        result = skey.get_all_key_names()
    else:
        # Return all keys
        result = skey.keys
    return jsonify({'data': result})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5002')
