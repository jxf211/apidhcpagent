#!/usr/bin/env python
# encoding: utf-8
from flask import Blueprint
from flask import request
from const import API_PREFIX
from utils import json_http_response

dhcp_app = Blueprint('dhcp_app', __name__)

@dhcp_app.route(
    API_PREFIX + '/dhcp/<int:network_id>/', methods=['POST'])
def network_create_end(network_id):
    pass
