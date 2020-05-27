#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, request
from flask_jsonpify import jsonify
from servertools import ServerHosts, ServerKeys, HueBulb

app = Flask(__name__)
shost = ServerHosts()
skey = ServerKeys()


@app.route('/toggle-lights', methods=['GET'])
def hosts():
    """Simple GET all hosts with static IPs"""
    light_name = request.args.get('name', default=None, type=str)
    if light_name is None:
        raise ValueError('No light name selected')
    h = HueBulb(light_name)
    h.toggle()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5003')
