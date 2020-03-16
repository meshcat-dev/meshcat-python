from __future__ import absolute_import, division, print_function

import base64
import os
import sys
import multiprocessing
from collections import deque

if sys.version_info >= (3, 0):
    ADDRESS_IN_USE_ERROR = OSError
else:
    import socket
    ADDRESS_IN_USE_ERROR = socket.error

import tornado.web
import tornado.ioloop
import tornado.websocket
import tornado.gen

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop.zmqstream import ZMQStream

from .tree import SceneTree, walk, find_node

# Install ZMQ ioloop instead of a tornado ioloop
# http://zeromq.github.com/pyzmq/eventloop.html
ioloop.install()


VIEWER_ROOT = os.path.join(os.path.dirname(__file__), "..", "viewer", "dist")
VIEWER_HTML = "index.html"

DEFAULT_FILESERVER_PORT = 7000
MAX_ATTEMPTS = 1000
DEFAULT_ZMQ_METHOD = "tcp"
DEFAULT_ZMQ_PORT = 6000

MESHCAT_COMMANDS = ["set_transform", "set_object", "delete", "set_property", "set_animation"]


def find_available_port(func, default_port, max_attempts=MAX_ATTEMPTS):
    for i in range(max_attempts):
        port = default_port + i
        try:
            return func(port), port
        except (ADDRESS_IN_USE_ERROR, zmq.error.ZMQError):
            print("Port: {:d} in use, trying another...".format(port), file=sys.stderr)
        except Exception as e:
            print(type(e))
            raise
    else:
        raise(Exception("Could not find an available port in the range: [{:d}, {:d})".format(default_port, max_attempts + default_port)))


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        self.bridge = kwargs.pop("bridge")
        super(WebSocketHandler, self).__init__(*args, **kwargs)

    def open(self):
        self.bridge.websocket_pool.add(self)
        print("opened:", self, file=sys.stderr)
        self.bridge.send_scene(self)

    def on_message(self, message):
        pass

    def on_close(self):
        self.bridge.websocket_pool.remove(self)
        print("closed:", self, file=sys.stderr)


def create_command(data):
    """Encode the drawing command into a Javascript fetch() command for display."""
    return """
fetch("data:application/octet-binary;base64,{}")
    .then(res => res.arrayBuffer())
    .then(buffer => viewer.handle_command_bytearray(new Uint8Array(buffer)));
    """.format(base64.b64encode(data).decode("utf-8"))


class ZMQWebSocketBridge(object):
    context = zmq.Context()

    def __init__(self, zmq_url=None, host="127.0.0.1", port=None):
        self.host = host
        self.websocket_pool = set()
        self.app = self.make_app()
        self.ioloop = tornado.ioloop.IOLoop.current()

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

        self.tree = SceneTree()

    def make_app(self):
        return tornado.web.Application([
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": VIEWER_ROOT, "default_filename": VIEWER_HTML}),
            (r"/", WebSocketHandler, {"bridge": self})
        ])

    def wait_for_websockets(self):
        if len(self.websocket_pool) > 0:
            self.zmq_socket.send(b"ok")
        else:
            self.ioloop.call_later(0.1, self.wait_for_websockets)

    def handle_zmq(self, frames):
        cmd = frames[0].decode("utf-8")
        if cmd == "url":
            self.zmq_socket.send(self.web_url.encode("utf-8"))
        elif cmd == "wait":
            self.ioloop.add_callback(self.wait_for_websockets)
        elif cmd in MESHCAT_COMMANDS:
            if len(frames) != 3:
                self.zmq_socket.send(b"error: expected 3 frames")
                return
            path = list(filter(lambda x: len(x) > 0, frames[1].decode("utf-8").split("/")))
            data = frames[2]
            self.forward_to_websockets(frames)
            if cmd == "set_transform":
                find_node(self.tree, path).transform = data
            elif cmd == "set_object":
                find_node(self.tree, path).object = data
            elif cmd == "delete":
                if len(path) > 0:
                    parent = find_node(self.tree, path[:-1])
                    child = path[-1]
                    if child in parent:
                        del parent[child]
                else:
                    self.tree = SceneTree()
            self.zmq_socket.send(b"ok")
        elif cmd == "get_scene":
            # when the server gets this command, return the tree
            # as a series of msgpack-backed binary blobs
            drawing_commands = ""
            for node in walk(self.tree):
                if node.object is not None:
                    drawing_commands += create_command(node.object)
                if node.transform is not None:
                    drawing_commands += create_command(node.transform)

            # now that we have the drawing commands, generate the full
            # HTML that we want to generate, including the javascript assets
            mainminjs_path = os.path.join(VIEWER_ROOT, "main.min.js")
            mainminjs_src = ""
            with open(mainminjs_path, "r") as f:
                mainminjs_src = f.readlines()
            mainminjs_src = "".join(mainminjs_src)

            html = """
                <!DOCTYPE html>
                <html>
                    <head> <meta charset=utf-8> <title>MeshCat</title> </head>
                    <body>
                        <div id="meshcat-pane">
                        </div>
                        <script>
                            {mainminjs}
                        </script>
                        <script>
                            var viewer = new MeshCat.Viewer(document.getElementById("meshcat-pane"));
                            {commands}
                        </script>
                         <style>
                            body {{margin: 0; }}
                            #meshcat-pane {{
                                width: 100vw;
                                height: 100vh;
                                overflow: hidden;
                            }}
                        </style>
                        <script id="embedded-json"></script>
                    </body>
                </html>
            """.format(mainminjs=mainminjs_src, commands=drawing_commands)
            self.zmq_socket.send(html.encode('utf-8'))
        else:
            self.zmq_socket.send(b"error: unrecognized comand")

    def forward_to_websockets(self, frames):
        cmd, path, data = frames
        for websocket in self.websocket_pool:
            websocket.write_message(data, binary=True)

    def setup_zmq(self, url):
        zmq_socket = self.context.socket(zmq.REP)
        zmq_socket.bind(url)
        zmq_stream = ZMQStream(zmq_socket)
        zmq_stream.on_recv(self.handle_zmq)
        return zmq_socket, zmq_stream, url

    def send_scene(self, websocket):
        for node in walk(self.tree):
            if node.object is not None:
                websocket.write_message(node.object, binary=True)
            if node.transform is not None:
                websocket.write_message(node.transform, binary=True)

    def run(self):
        self.ioloop.start()


def main():
    import argparse
    import sys
    import webbrowser

    parser = argparse.ArgumentParser(description="Serve the MeshCat HTML files and listen for ZeroMQ commands")
    parser.add_argument('--zmq-url', '-z', type=str, nargs="?", default=None)
    parser.add_argument('--open', '-o', action="store_true")
    results = parser.parse_args()
    bridge = ZMQWebSocketBridge(zmq_url=results.zmq_url)
    print("zmq_url={:s}".format(bridge.zmq_url))
    print("web_url={:s}".format(bridge.web_url))
    if results.open:
        webbrowser.open(bridge.web_url, new=2)

    bridge.run()

if __name__ == '__main__':
    main()
