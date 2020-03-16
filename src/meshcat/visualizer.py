from __future__ import absolute_import, division, print_function

import atexit
import sys
import subprocess
import webbrowser

import umsgpack
import numpy as np
import zmq
import re

from .path import Path
from .commands import SetObject, SetTransform, Delete, SetAnimation
from .geometry import MeshPhongMaterial


def capture(pattern, s):
    match = re.match(pattern, s)
    if not match:
        raise ValueError("Could not match {:s} with pattern {:s}".format(s, pattern))
    else:
        return match.groups()[0]

def match_zmq_url(line):
    return capture(r"^zmq_url=(.*)$", line)

def match_web_url(line):
    return capture(r"^web_url=(.*)$", line)


class ViewerWindow:
    context = zmq.Context()

    def __init__(self, zmq_url, start_server):
        if start_server:
            # Need -u for unbuffered output: https://stackoverflow.com/a/25572491
            args = [sys.executable, "-u", "-m", "meshcat.servers.zmqserver"]
            if zmq_url is not None:
                args.append("--zmq-url")
                args.append(zmq_url)
            self.server_proc = subprocess.Popen(args, stdout=subprocess.PIPE)
            self.zmq_url = match_zmq_url(self.server_proc.stdout.readline().strip().decode("utf-8"))
            self.web_url = match_web_url(self.server_proc.stdout.readline().strip().decode("utf-8"))

            def cleanup():
                self.server_proc.kill()
                self.server_proc.wait()

            atexit.register(cleanup)

        else:
            self.server_proc = None
            self.zmq_url = zmq_url

        self.connect_zmq()

        if not start_server:
            self.web_url = self.request_web_url()
            # Not sure why this is necessary, but requesting the web URL before
            # the websocket connection is made seems to break the receiver
            # callback in the server until we reconnect.
            self.connect_zmq()

        print("You can open the visualizer by visiting the following URL:")
        print(self.web_url)



    def connect_zmq(self):
        self.zmq_socket = self.context.socket(zmq.REQ)
        self.zmq_socket.connect(self.zmq_url)

    def request_web_url(self):
        self.zmq_socket.send(b"url")
        response = self.zmq_socket.recv().decode("utf-8")
        return response

    def open(self):
        webbrowser.open(self.web_url, new=2)
        return self

    def wait(self):
        self.zmq_socket.send(b"wait")
        return self.zmq_socket.recv().decode("utf-8")

    def send(self, command):
        cmd_data = command.lower()
        self.zmq_socket.send_multipart([
            cmd_data["type"].encode("utf-8"),
            cmd_data["path"].encode("utf-8"),
            umsgpack.packb(cmd_data)
        ])
        self.zmq_socket.recv()

    def get_scene(self):
        """Get the static HTML from the ZMQ server."""
        self.zmq_socket.send(b"get_scene")
        # we receive the HTML as utf-8-encoded, so decode here
        return self.zmq_socket.recv().decode('utf-8')


class Visualizer:
    __slots__ = ["window", "path"]

    def __init__(self, zmq_url=None, window=None):
        if window is None:
            self.window = ViewerWindow(zmq_url=zmq_url, start_server=(zmq_url is None))
        else:
            self.window = window
        self.path = Path(("meshcat",))

    @staticmethod
    def view_into(window, path):
        vis = Visualizer(window=window)
        vis.path = path
        return vis

    def open(self):
        self.window.open()
        return self

    def url(self):
        return self.window.web_url

    def wait(self):
        """
        Block until a browser is connected to the server
        """
        return self.window.wait()

    def jupyter_cell(self):
        from IPython.display import HTML
        return HTML("""
<div style="height: 400px; width: 600px; overflow-x: auto; overflow-y: hidden; resize: both">
<iframe src="{url}" style="width: 100%; height: 100%; border: none"></iframe>
</div>
""".format(url=self.url()))

    def __getitem__(self, path):
        return Visualizer.view_into(self.window, self.path.append(path))

    def set_object(self, geometry, material=None):
        return self.window.send(SetObject(geometry, material, self.path))

    def set_transform(self, matrix=np.eye(4)):
        return self.window.send(SetTransform(matrix, self.path))

    def set_animation(self, animation, play=True, repetitions=1):
        return self.window.send(SetAnimation(animation, play=play, repetitions=repetitions))

    def delete(self):
        return self.window.send(Delete(self.path))

    def close(self):
        self.window.close()

    def static_html(self):
        """
        Generate and save a static HTML file that standalone encompasses the visualizer and contents.
        
        Ask the server for the scene (since the server knows it), and pack it all into an
        HTML blob for future use.
        """
        return self.window.get_scene()

    def __repr__(self):
        return "<Visualizer using: {window} at path: {path}>".format(window=self.window, path=self.path)


if __name__ == '__main__':
    import time
    import sys

    if len(sys.argv) > 1:
        zmq_url = sys.argv[1]
    else:
        zmq_url = None

    window = ViewerWindow(zmq_url, zmq_url is None, True)

    while True:
        time.sleep(100)

