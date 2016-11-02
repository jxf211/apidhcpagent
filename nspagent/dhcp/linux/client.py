# Copyright (c) 2014 Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging
from multiprocessing import managers
from multiprocessing import util as mp_util
import os
import subprocess
import threading
import weakref

try:
    import eventlet.patcher
except ImportError:
    patched_socket = False
else:
    # In tests patching happens later, so we'll rely on environment variable
    patched_socket = (eventlet.patcher.is_monkey_patched('socket') or
                      os.environ.get('TEST_EVENTLET', False))

#import jsonrpc


# Copyright (c) 2014 Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import functools
import os
import shutil
import signal
import stat
import sys
import tempfile
import wrapper

LOG = logging.getLogger(__name__)

# Since multiprocessing supports only pickle and xmlrpclib for serialization of
# RPC requests and responses, we declare another 'jsonrpc' serializer

#managers.listener_client['jsonrpc'] = jsonrpc.JsonListener, jsonrpc.JsonClient


class RootwrapClass(object):
    def __init__(self, config, filters):
        self.config = config
        self.filters = filters

    def run_one_command(self, userargs, stdin=None):
        obj = wrapper.start_subprocess(
            self.filters, userargs,
            exec_dirs=self.config.exec_dirs,
            log=self.config.use_syslog,
            close_fds=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = obj.communicate(stdin)
        return obj.returncode, out, err

    def shutdown(self):
        # Suicide to force break of the main thread
        os.kill(os.getpid(), signal.SIGINT)

'''
def get_manager_class(config=None, filters=None):
    class RootwrapManager(managers.BaseManager):
        def __init__(self, address=None, authkey=None):
            # Force jsonrpc because neither pickle nor xmlrpclib is secure
            super(RootwrapManager, self).__init__(address, authkey,
                                                  serializer='jsonrpc')

    if config is not None:
        partial_class = functools.partial(RootwrapClass, config, filters)
        RootwrapManager.register('rootwrap', partial_class)
    else:
        RootwrapManager.register('rootwrap')

    return RootwrapManager

def daemon_start(config, filters):
    temp_dir = tempfile.mkdtemp(prefix='rootwrap-')
    LOG.debug("Created temporary directory %s", temp_dir)
    try:
        # allow everybody to find the socket
        rwxr_xr_x = (stat.S_IRWXU |
                     stat.S_IRGRP | stat.S_IXGRP |
                     stat.S_IROTH | stat.S_IXOTH)
        os.chmod(temp_dir, rwxr_xr_x)
        socket_path = os.path.join(temp_dir, "rootwrap.sock")
        LOG.debug("Will listen on socket %s", socket_path)
        manager_cls = get_manager_class(config, filters)
        manager = manager_cls(address=socket_path)
        server = manager.get_server()
        # allow everybody to connect to the socket
        rw_rw_rw_ = (stat.S_IRUSR | stat.S_IWUSR |
                     stat.S_IRGRP | stat.S_IWGRP |
                     stat.S_IROTH | stat.S_IWOTH)
        os.chmod(socket_path, rw_rw_rw_)
        try:
            # In Python 3 we have to use buffer to push in bytes directly
            stdout = sys.stdout.buffer
        except AttributeError:
            stdout = sys.stdout
        stdout.write(socket_path.encode('utf-8'))
        stdout.write(b'\n')
        stdout.write(bytes(server.authkey))
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()
        # Gracefully shutdown on INT or TERM signals
        stop = functools.partial(daemon_stop, server)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        LOG.info("Starting rootwrap daemon main loop")
        server.serve_forever()
    finally:
        conn = server.listener
        # This will break accept() loop with EOFError if it was not in the main
        # thread (as in Python 3.x)
        conn.close()
        # Closing all currently connected client sockets for reading to break
        # worker threads blocked on recv()
        for cl_conn in conn.get_accepted():
            try:
                cl_conn.half_close()
            except Exception:
                # Most likely the socket have already been closed
                LOG.debug("Failed to close connection")
        LOG.info("Waiting for all client threads to finish.")
        for thread in threading.enumerate():
            if thread.daemon:
                LOG.debug("Joining thread %s", thread)
                thread.join()
        LOG.debug("Removing temporary directory %s", temp_dir)
        shutil.rmtree(temp_dir)


def daemon_stop(server, signal, frame):
    LOG.info("Got signal %s. Shutting down server", signal)
    # Signals are caught in the main thread which means this handler will run
    # in the middle of serve_forever() loop. It will catch this exception and
    # properly return. Since all threads created by server_forever are
    # daemonic, we need to join them afterwards. In Python 3 we can just hit
    # stop_event instead.
    try:
        server.stop_event.set()
    except AttributeError:
        raise KeyboardInterrupt


if patched_socket:
    # We have to use slow version of recvall with eventlet because of a bug in
    # GreenSocket.recv_into:
    # https://bitbucket.org/eventlet/eventlet/pull-request/41
    # This check happens here instead of jsonrpc to avoid importing eventlet
    # from daemon code that is run with root priviledges.
    jsonrpc.JsonConnection.recvall = jsonrpc.JsonConnection._recvall_slow

try:
    finalize = weakref.finalize
except AttributeError:
    def finalize(obj, func, *args, **kwargs):
        return mp_util.Finalize(obj, func, args=args, kwargs=kwargs,
                                exitpriority=0)

ClientManager = get_manager_class()
LOG = logging.getLogger(__name__)

class Client(object):
    def __init__(self, rootwrap_daemon_cmd):
        self._start_command = rootwrap_daemon_cmd
        self._initialized = False
        self._mutex = threading.Lock()
        self._manager = None
        self._proxy = None
        self._process = None
        self._finalize = None

    def _initialize(self):
        if self._process is not None and self._process.poll() is not None:
            LOG.warning("Leaving behind already spawned process with pid %d, "
                        "root should kill it if it's still there (I can't)",
                        self._process.pid)

        process_obj = subprocess.Popen(self._start_command,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        LOG.info("Spawned new rootwrap daemon process with pid=%d",
                 process_obj.pid)

        self._process = process_obj
        socket_path = process_obj.stdout.readline()[:-1]
        # For Python 3 we need to convert bytes to str here
        if not isinstance(socket_path, str):
            socket_path = socket_path.decode('utf-8')
        authkey = process_obj.stdout.read(32)
        if process_obj.poll() is not None:
            stderr = process_obj.stderr.read()
            # NOTE(yorik-sar): don't expose stdout here
            raise Exception("Failed to spawn rootwrap process.\nstderr:\n%s" %
                            (stderr,))
        self._manager = ClientManager(socket_path, authkey)
        self._manager.connect()
        self._proxy = self._manager.rootwrap()
        self._finalize = finalize(self, self._shutdown, self._process,
                                  self._manager)
        self._initialized = True

    @staticmethod
    def _shutdown(process, manager, JsonClient=jsonrpc.JsonClient):
        # Storing JsonClient in arguments because globals are set to None
        # before executing atexit routines in Python 2.x
        if process.poll() is None:
            LOG.info('Stopping rootwrap daemon process with pid=%s',
                     process.pid)
            try:
                manager.rootwrap().shutdown()
            except (EOFError, IOError):
                pass  # assume it is dead already
            # We might want to wait for process to exit or kill it, but we
            # can't provide sane timeout on 2.x and we most likely don't have
            # permisions to do so
        # Invalidate manager's state so that proxy won't try to do decref
        manager._state.value = managers.State.SHUTDOWN

    def _ensure_initialized(self):
        with self._mutex:
            if not self._initialized:
                self._initialize()

    def _restart(self, proxy):
        with self._mutex:
            assert self._initialized
            # Verify if someone has already restarted this.
            if self._proxy is proxy:
                self._finalize()
                self._manager = None
                self._proxy = None
                self._initialized = False
                self._initialize()
            return self._proxy

    def execute(self, cmd, stdin=None):
        self._ensure_initialized()
        proxy = self._proxy
        retry = False
        try:
            res = proxy.run_one_command(cmd, stdin)
        except (EOFError, IOError):
            retry = True
        # res can be None if we received final None sent by dying server thread
        # instead of response to our request. Process is most likely to be dead
        # at this point.
        if retry or res is None:
            proxy = self._restart(proxy)
            res = proxy.run_one_command(cmd, stdin)
        return res
'''
