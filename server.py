# -*- coding:utf-8 -*-

import ssl
import socket
import logging
import eventlet
import eventlet.wsgi
import greenlet

log = logging.getLogger(__name__)

class Server(object):
    """Server class to manage multiple WSGI sockets and applications."""

    def __init__(self, application, host=None, port=None,
                 keepalive=True, keepidle=None, threads=1000):
        self.application = application
        self.host = host or '127.0.0.1'
        self.port = port or 0
        self.pool = eventlet.GreenPool(threads)
        self.greenthread = None
        self.do_ssl = False
        self.cert_required = False
        self.keepalive = keepalive
        self.keepidle = keepidle
        self.socket = None

    def listen(self, backlog=128):
        """Create and start listening on socket.
        """
        try:
            info = socket.getaddrinfo(self.host,
                                      self.port,
                                      socket.AF_UNSPEC,
                                      socket.SOCK_STREAM)[0]
            self.socket = eventlet.listen(info[-1], family=info[0],
                                          backlog=backlog)
        except EnvironmentError:
            log.error("Could not bind to %s:%s" % (self.host, self.port))
            raise

        log.info('Starting on %s:%s' % (self.host, self.port))

    def start(self, backlog=128):
        """Run a WSGI server with the given application."""

        if self.socket is None:
            self.listen(backlog=backlog)

        dup_socket = self.socket.dup()

        # SSL is enabled
        if self.do_ssl:
            if self.cert_required:
                cert_reqs = ssl.CERT_REQUIRED
            else:
                cert_reqs = ssl.CERT_NONE

            dup_socket = eventlet.wrap_ssl(dup_socket, certfile=self.certfile,
                                           keyfile=self.keyfile,
                                           server_side=True,
                                           cert_reqs=cert_reqs,
                                           ca_certs=self.ca_certs)

        # Optionally enable keepalive on the wsgi socket.
        if self.keepalive:
            dup_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # This option isn't available in the OS X version of eventlet
            if hasattr(socket, 'TCP_KEEPIDLE') and self.keepidle is not None:
                dup_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,
                                      self.keepidle)

        self.greenthread = self.pool.spawn(self._run,
                                           self.application,
                                           dup_socket)

    def set_ssl(self, certfile, keyfile=None, ca_certs=None,
                cert_required=True):
        self.certfile = certfile
        self.keyfile = keyfile
        self.ca_certs = ca_certs
        self.cert_required = cert_required
        self.do_ssl = True

    def stop(self):
        if self.greenthread is not None:
            self.greenthread.kill()

    def wait(self):
        """Wait until all servers have completed running."""
        try:
            self.pool.waitall()
        except KeyboardInterrupt:
            pass
        except greenlet.GreenletExit:
            pass

    def reset(self):
        pass

    def _run(self, application, socket):
        """Start a WSGI server in a new green thread."""
        try:
            eventlet.wsgi.server(socket, application, custom_pool=self.pool,
                                 debug=False)
        except greenlet.GreenletExit:
            # Wait until all servers have completed running
            pass
        except Exception:
            log.error('Server error')
            raise
