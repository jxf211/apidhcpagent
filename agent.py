#!/usr/bin/env python
# encoding: utf-8

class DhcpAgent(object):
    def __init__(self, host=None):
        self.cache = NetworkCache()
        self.dhcp_driver_cls
