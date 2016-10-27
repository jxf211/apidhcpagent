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
LOG = logging.getLogger(__name__)

def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    """
    do the UNIX double-fork magic, see Stevens' "Advanced
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    """
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

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

if __name__== '__main__':
    register_options()
    common_config.init(sys.argv[1:])
    config.setup_logging()

    #parser = argparse.ArgumentParser()
    #parser.add_argument("-d", "--daemon", help="run in background",
    #                    action="store_true")

    #args = parser.parse_args()
    #if args.daemon and os.getppid() != 1:
    #    daemonize()

    signal.signal(signal.SIGTERM, sigterm_handler)

   # init_logger(args)
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

