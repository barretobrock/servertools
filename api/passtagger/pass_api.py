#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from flask import Flask, request, render_template, redirect
from wtforms import Form, StringField, SelectField, PasswordField, FileField, validators
from pykeepass import PyKeePass
from kavalkilu import LogWithInflux
from servertools import get_secret_file

app = Flask(__name__)


class DataStore:
    kpdb = None
    DB_DIR = os.path.join(os.path.expanduser('~'), *['Dropbox', 'Documents', 'salas6nad'])

    def __init__(self):
        pass

    def read_kpbd(self, filename: str, pw: str):
        full_path = os.path.join(self.DB_DIR, filename)
        self.kpdb = PyKeePass(full_path, pw)


class SearchForm(Form):
    choices = [('tag', 'tag'), ('entry', 'entry')]
    select = SelectField('Search for entries: ', choices=choices)
    search = StringField('')


class InitializeForm(Form):
    db_path = FileField('KDBX Location')
    file_pw = PasswordField('Enter password for file')


dstore = DataStore()


@app.route('/', methods=['GET', 'POST'])
def main_page():
    search = SearchForm(request.form)
    if request.method == 'POST':
        return search_results(search)
    return render_template('index.html', form=search)


@app.route('/load', methods=['GET'])
def load_file():
    return render_template('load.html')


@app.route('/initialize', methods=['POST'])
def initialize():
    uploaded_file = request.files['file'].filename
    pw = request.values['password']
    dstore.read_kpbd(uploaded_file, pw)
    return redirect('/')


@app.route('/results')
def search_results(search: SearchForm):
    search_string = search.data.get('search', '')
    results = dstore.kpdb.find_entries(title=search_string, regex=True, flags='i')

    return render_template('results.html', results=results)


@app.errorhandler(500)
def handle_errors(error):
    return 'Not found!'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5004')
    # Instantiate log here, as the hosts API is requested to communicate with influx
    # log = LogWithInflux('passtagger')
