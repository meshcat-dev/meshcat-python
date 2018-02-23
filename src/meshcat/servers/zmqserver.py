from __future__ import absolute_import, division, print_function

import os
import sys
import multiprocessing
from collections import deque

import tornado.web
import tornado.ioloop
import tornado.websocket
import tornado.gen

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop.zmqstream import ZMQStream

# Install ZMQ ioloop instead of a tornado ioloop
# http://zeromq.github.com/pyzmq/eventloop.html
ioloop.install()


VIEWER_ROOT = os.path.join(os.path.dirname(__file__), "..", "viewer", "static")
VIEWER_HTML = "meshcat.html"

DEFAULT_FILESERVER_PORT = 7000
MAX_ATTEMPTS = 1000
DEFAULT_ZMQ_METHOD = "tcp"
DEFAULT_ZMQ_PORT = 6000


def find_available_port(func, default_port, max_attempts=MAX_ATTEMPTS):
    for i in range(max_attempts):
        port = default_port + i
        try:
            return func(port), port
        except (OSError, zmq.error.ZMQError):
            print("Port: {:d} in use, trying another...".format(port), file=sys.stderr)
            pass
    else:
        raise(Exception("Could not find an available port in the range: [{:d}, {:d})".format(default_port, max_attempts + default_port)))


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        self.bridge = kwargs.pop("bridge")
        super(WebSocketHandler, self).__init__(*args, **kwargs)

    def open(self):
        self.bridge.websocket_pool.add(self)
        self.bridge.process_pending_messages()
        print("opened:", self, file=sys.stderr)

    def on_message(self, message):
        pass

    def on_close(self):
        self.bridge.websocket_pool.remove(self)
        print("closed:", self, file=sys.stderr)


class ZMQWebSocketBridge(object):
    context = zmq.Context()

    def __init__(self, zmq_url=None, host="127.0.0.1", port=None):
        self.host = host
        self.websocket_pool = set()
        self.app = self.make_app()

        if zmq_url is None:
            def f(port):
                return self.setup_zmq("{:s}://{:s}:{:d}".format(DEFAULT_ZMQ_METHOD, self.host, port))
            (self.zmq_socket, self.zmq_stream, self.zmq_url), _ = find_available_port(f, DEFAULT_ZMQ_PORT)
        else:
            self.zmq_socket, self.zmq_stream, self.zmq_url = self.setup_zmq(zmq_url)

        if port is None:
            _, self.fileserver_port = find_available_port(self.app.listen, DEFAULT_FILESERVER_PORT)
        else:
            self.app.listen(port)
            self.fileserver_port = port
        self.web_url = "http://{host}:{port}/static/".format(host=self.host, port=self.fileserver_port)
        self.pending_messages = deque()

    def make_app(self):
        return tornado.web.Application([
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": VIEWER_ROOT, "default_filename": VIEWER_HTML}),
            (r"/", WebSocketHandler, {"bridge": self})
        ])

    def handle_zmq(self, msg):
        if len(msg) == 1 and len(msg[0]) == 0:
            self.zmq_socket.send(self.web_url.encode("utf-8"))
        else:
            self.send_to_websockets(msg)

    def send_to_websockets(self, msg):
        self.pending_messages.append(msg)
        self.process_pending_messages()

    def process_pending_messages(self):
        while len(self.pending_messages) > 0 and len(self.websocket_pool) > 0:
            msg = self.pending_messages.popleft()
            for websocket in self.websocket_pool:
                websocket.write_message(msg[0], binary=True)
            self.zmq_socket.send(b"ok")

    def setup_zmq(self, url):
        zmq_socket = self.context.socket(zmq.REP)
        zmq_socket.bind(url)
        zmq_stream = ZMQStream(zmq_socket)
        zmq_stream.on_recv(self.handle_zmq)
        return zmq_socket, zmq_stream, url

    def run(self):
        tornado.ioloop.IOLoop.current().start()


# def _run_server(queue, **kwargs):
#     queue.put((bridge.zmq_url, bridge.web_url))

# def create_server(*args, **kwargs):
#     queue = multiprocessing.Queue()
#     proc = multiprocessing.Process(target=_run_server, args=(queue,), kwargs=kwargs)
#     proc.daemon = True
#     proc.start()
#     return proc, queue.get()

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Serve the MeshCat HTML files and listen for ZeroMQ commands")
    parser.add_argument('--zmq_url', '-z', type=str, nargs="?", default=None)
    parser.add_argument('--open', '-o', action="store_true")
    parser.parse_args()

    if len(sys.argv) > 1:
        zmq_url = sys.argv[1]
    else:
        zmq_url = None
    bridge = ZMQWebSocketBridge(zmq_url=zmq_url)
    print(bridge.zmq_url)
    print(bridge.web_url)
    bridge.run()

if __name__ == '__main__':
    main()
