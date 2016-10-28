#!/usr/bin/env python
# encoding: utf-8
from common import eventlet_utils
eventlet_utils.monkey_patch()
import argparse
import os
import signal
import sys
import traceback
from oslo_config import cfg
from utils import get_ip_address
from common import config as common_config
from nspagent.dhcpcommon import config
from nspagent.dhcp.linux import interface
from nspagent.dhcp import config as dhcp_config
from oslo_log import log as logging
from server import Server
from router import API
from nspagent.dhcp.linux import daemon

LOG = logging.getLogger(__name__)

def register_options():
    config.register_interface_driver_opts_helper(cfg.CONF)
    config.register_use_namespaces_opts_helper(cfg.CONF)
    config.register_agent_state_opts_helper(cfg.CONF)
    cfg.CONF.register_opts(dhcp_config.DHCP_AGENT_OPTS)
    cfg.CONF.register_opts(dhcp_config.DHCP_OPTS)
    cfg.CONF.register_opts(dhcp_config.DNSMASQ_OPTS)
    #cfg.CONF.register_opts(metadata_config.DRIVER_OPTS)
    #cfg.CONF.register_opts(metadata_config.SHARED_OPTS)
    cfg.CONF.register_opts(interface.OPTS)

def sigterm_handler(signal, frame):
        sys.exit(0)

class DeamonMain(daemon.Daemon):
    def __init__(self, ip, port):
        self.register_options()
        common_config.init(sys.argv[1:])
        config.setup_logging()
        self._ip = ip
        self._port = port
        super(DeamonMain, self).__init__('/var/dhcp/pid')

    def run(self):
        super(DeamonMain, self).run()
        signal.signal(signal.SIGTERM, sigterm_handler)
        LOG.info('Launching DhcpAgent API Stack (DHCP_AGENT) ...')
        try:
            LOG.info('Gevent approaching ... server ip:%s port:%s',
                        self._ip, self._port)
            app = API()
            server = Server(app, host=self._ip, port=self._port)
            server.start()
            server.wait()
        except Exception as e:
            LOG.error('Exception: %s' % e)
            LOG.error('%s' % traceback.format_exc())
            sys.exit(1)

    def register_options():
        config.register_interface_driver_opts_helper(cfg.CONF)
        config.register_use_namespaces_opts_helper(cfg.CONF)
        config.register_agent_state_opts_helper(cfg.CONF)
        cfg.CONF.register_opts(dhcp_config.DHCP_AGENT_OPTS)
        cfg.CONF.register_opts(dhcp_config.DHCP_OPTS)
        cfg.CONF.register_opts(dhcp_config.DNSMASQ_OPTS)
        cfg.CONF.register_opts(interface.OPTS)

if __name__== '__main__':
    main = DeamonMain("192.168.49.22", "20010")
    main.start()
'''
    register_options()
    common_config.init(sys.argv[1:])
    config.setup_logging()

    signal.signal(signal.SIGTERM, sigterm_handler)

    LOG.info('Launching DhcpAgent API Stack (DHCP_AGENT) ...')

    #local_ctrl_ip = get_ip_address("nspbr0")
    local_ctrl_ip = "192.168.49.22"
    try:
        LOG.info('Gevent approaching ... server ip:%s', local_ctrl_ip)
        app = API()
        server = Server(app, host=local_ctrl_ip , port="20010")
        server.start()
        server.wait()
    except Exception as e:
        LOG.error('Exception: %s' % e)
        LOG.error('%s' % traceback.format_exc())
        sys.exit(1)
'''
