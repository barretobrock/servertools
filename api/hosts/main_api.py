#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask
from servertools import get_secret_file
from api.hosts.hosts import hosts
from api.hosts.keys import keys

app = Flask(__name__)
for blueprint in [keys, hosts]:
    app.register_blueprint(blueprint)


@app.route('/')
def main_page():
    return 'Main page!'


@app.errorhandler(500)
def handle_errors(error):
    return 'Not found!'


if __name__ == '__main__':
    secret_key = get_secret_file('FLASK_SECRET')
    app.secret_key = secret_key
    app.run(host='0.0.0.0', port='5002')
