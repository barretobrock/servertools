#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, request, render_template
from servertools import ServerHosts, ServerKeys, HueBulb, HueSensor, RokuTV

app = Flask(__name__)
shost = ServerHosts()
skey = ServerKeys()


def return_html(msg: str):
    return f"""
        <style>
            * {{
                background-color: black;
                color: white;
            }}
        </style>
        <div>{msg}</div>
    """


@app.route('/')
def main_page():
    return 'Home Automation API'


@app.route('/toggle-light', methods=['GET'])
def light_toggle():
    """Toggle lights on/off"""
    light_name = request.args.get('name', default=None, type=str)
    if light_name is None:
        raise ValueError('No light name selected')
    light_names = []
    if light_name in ['garage', 'stairs']:
        # Handle both lights
        for i in [1, 2]:
            light = f'{light_name}-{i}'
            h = HueBulb(light)
            h.toggle()
            light_names.append(light)
    else:
        h = HueBulb(light_name)
        h.toggle()
        light_names.append(light_name)
    return return_html(f'{" and ".join(light_names)} set to {h.get_status()}')


@app.route('/toggle-sensor', methods=['GET'])
def sensor_toggle():
    """Toggle motion sensors on/off"""
    sensor_name = request.args.get('name', default=None, type=str)
    if sensor_name is None:
        raise ValueError('No sensor name selected')
    s = HueSensor(sensor_name)
    s.toggle()
    return return_html(msg=f'{s.name} set to {s.on}.')


@app.route('/tv', methods=['GET'])
def tv_action():
    """Toggle motion sensors on/off"""
    action = request.args.get('action', default=None, type=str)
    if action is None:
        raise ValueError('No action selected')
    tv = RokuTV()
    if action == 'toggle':
        tv.power()
        msg = 'TV power toggled'
    elif action == 'mute':
        tv.mute()
        msg = 'TV mute toggled'
    else:
        msg = f'Unknown action: {action}'
    return return_html(msg=msg)


@app.errorhandler(404)
def not_found_error(error):
    return 'Error!!', 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5003')
