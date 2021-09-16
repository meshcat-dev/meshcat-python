import webbrowser
import umsgpack
import numpy as np
import zmq
import io
from PIL import Image        
from IPython.display import HTML


from .path import Path
from .commands import SetObject, SetTransform, Delete, SetProperty, SetAnimation, CaptureImage
from .geometry import MeshPhongMaterial
from .servers.zmqserver import start_zmq_server_as_subprocess

class ViewerWindow:
    context = zmq.Context()

    def __init__(self, zmq_url, start_server, server_args):
        if start_server:
            self.server_proc, self.zmq_url, self.web_url = start_zmq_server_as_subprocess(
                zmq_url=zmq_url, server_args=server_args)

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

    def get_image(self):
        cmd_data = CaptureImage().lower()
        self.zmq_socket.send_multipart([
            cmd_data["type"].encode("utf-8"),
            "".encode("utf-8"),
            umsgpack.packb(cmd_data)
        ])
        img_bytes = self.zmq_socket.recv()
        img = Image.open(io.BytesIO(img_bytes))
        return img


def srcdoc_escape(x):
    return x.replace("&", "&amp;").replace('"', "&quot;")


class Visualizer:
    __slots__ = ["window", "path"]

    def __init__(self, zmq_url=None, window=None, server_args=[]):
        if window is None:
            self.window = ViewerWindow(zmq_url=zmq_url, start_server=(zmq_url is None), server_args=server_args)
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

    def jupyter_cell(self, height=400):
        """
        Render the visualizer in a jupyter notebook or jupyterlab cell.

        For this to work, it should be the very last command in the given jupyter
        cell.
        """
        return HTML("""
            <div style="height: {height}px; width: 100%; overflow-x: auto; overflow-y: hidden; resize: both">
            <iframe src="{url}" style="width: 100%; height: 100%; border: none"></iframe>
            </div>
            """.format(url=self.url(), height=height))

    def render_static(self, height=400):
        """
        Render a static snapshot of the visualizer in a jupyter notebook or
        jupyterlab cell. The resulting snapshot of the visualizer will still be an
        interactive 3D scene, but it won't be affected by any future `set_transform`
        or `set_object` calls.

        Note: this method should work well even when your jupyter kernel is running
        on a different machine or inside a container.
        """
        return HTML("""
        <div style="height: {height}px; width: 100%; overflow-x: auto; overflow-y: hidden; resize: both">
        <iframe srcdoc="{srcdoc}" style="width: 100%; height: 100%; border: none"></iframe>
        </div>
        """.format(srcdoc=srcdoc_escape(self.static_html()), height=height))

    def __getitem__(self, path):
        return Visualizer.view_into(self.window, self.path.append(path))

    def set_object(self, geometry, material=None):
        return self.window.send(SetObject(geometry, material, self.path))

    def set_transform(self, matrix=np.eye(4)):
        return self.window.send(SetTransform(matrix, self.path))

    def set_property(self, key, value):
        return self.window.send(SetProperty(key, value, self.path))

    def set_animation(self, animation, play=True, repetitions=1):
        return self.window.send(SetAnimation(animation, play=play, repetitions=repetitions))

    def get_image(self):
        """Save an image"""
        return self.window.get_image()

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
    args = []
    if len(sys.argv) > 1:
        zmq_url = sys.argv[1]
        if len(sys.argv) > 2:
            args = sys.argv[2:]
    else:
        zmq_url = None

    window = ViewerWindow(zmq_url, zmq_url is None, True, args)

    while True:
        time.sleep(100)

