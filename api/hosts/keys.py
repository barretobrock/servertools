import json
from flask import Blueprint, redirect
from flask_jsonpify import jsonify
from servertools import Secrets, get_secret_file


keys = Blueprint('keys', __name__)

# Get password for secrets database
password = get_secret_file('SECRETPROP')
secrets = Secrets(password)


@keys.route('/keys/reload', methods=['GET'])
def reload_keys():
    secrets.load_database(password)
    return redirect('/keys')


@keys.route('/key/<key_name>', methods=['GET'])
def get_key(key_name: str):
    entry = secrets.get_entry(key_name)
    if entry is None:
        return {}
    if any([x is not None for x in [entry.username, entry.password]]):
        resp = {
            'un': entry.username,
            'pw': entry.password
        }
    else:
        resp = {}
    resp.update(entry.custom_properties)
    if len(entry.attachments) > 0:
        for att in entry.attachments:
            # For attachments, try to decode any that we might expect. For now, that's just JSON
            if isinstance(att.data, bytes):
                # Decode to string, try loading as json
                resp[att.filename] = json.loads(att.data.decode('utf-8'))
    return jsonify({'data': [resp]})


@keys.route('/keys', methods=['GET'])
def get_keys():
    """Simple GET all keys with static IPs"""
    # Get all available keys
    all_keys = secrets.db.entries
    results = sorted([f'{x.path} (m:{x.mtime.astimezone()})'
                      for x in all_keys if not x.path.startswith('hidden-')])
    return jsonify({'data': results})
