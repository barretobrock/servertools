from flask import Blueprint, request, redirect
from flask_jsonpify import jsonify
from servertools import ServerHosts


hosts = Blueprint('hosts', __name__)
shost = ServerHosts()


@hosts.route('/hosts/reload', methods=['GET'])
def reload_hosts():
    shost.reload()
    return redirect('/hosts')


@hosts.route('/hosts', methods=['GET'])
def all_hosts():
    return jsonify({'data': shost.all_hosts})


@hosts.route('/host', methods=['GET'])
def get_host():
    """Simple GET all hosts with static IPs"""
    host_name = request.args.get('name', default=None, type=str)
    ip = request.args.get('ip', default=None, type=str)
    result = []
    if host_name is not None:
        result.append(shost.get_ip(host_name))
    elif ip is not None:
        result.append(shost.get_host(ip))

    return jsonify({'data': result})
