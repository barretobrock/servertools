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
def get_hosts():
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
