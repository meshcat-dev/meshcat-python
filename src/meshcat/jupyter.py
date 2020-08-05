"""
A Visualizer for use in Jupyter notebooks or Google's Colaboratory.  It uses ipykernel.comm instead of zmq + websockets to establish a 1:1 connection
between python and the javascript viewer.  This was necessary, because colab
blocks insecure websockets (ws), and it is hard to establish and accept a
self-signed certificate for every cloud instance.

See https://github.com/RobotLocomotion/drake/issues/12645 for the detailed
origin story.
"""

from __future__ import absolute_import, division, print_function

import numpy as np
import os
import sys
import time
from IPython.display import HTML, display
from ipykernel import comm

from .path import Path
from .commands import SetObject, SetTransform, Delete, SetProperty, SetAnimation

running_in_colab = 'google.colab' in sys.modules

class JupyterVisualizer:
    __slots__ = ["path", "channel"]

    def __init__(self, write_html=True):
        self.path = Path(("meshcat",))
        self.channel = None
        if write_html:
            main_min = os.path.dirname(__file__) + '/viewer/dist/main.min.js'
            with open(main_min, "r") as f:
                main_min_js = f.read()

            if running_in_colab:
                display(HTML(f"""
<div id="meshcat-pane" style="height: 400px; width: 100%; overflow-x: auto; overflow-y: hidden; resize: both">
</div>

<script type="text/javascript">
{main_min_js}
</script>

<script>
    var viewer = new MeshCat.Viewer(document.getElementById("meshcat-pane"));
    google.colab.kernel.comms.registerTarget("meshcat", (comm, message) => {{
        viewer.handle_command(message.data)
    }});
    console.log("ready for meshcat comms");
</script>
"""))
            else:
                main_min_js = main_min_js.replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;").replace("'", "&apos;")
                display(HTML(f"""
<iframe srcdoc='
<div id="meshcat-pane" style="height: 400px; width: 100%; overflow-x: auto; overflow-y: hidden; resize: both">
</div>

<script type="text/javascript">
{main_min_js}
</script>

<script>
    var viewer = new MeshCat.Viewer(document.getElementById("meshcat-pane"));
    window.parent.Jupyter.notebook.kernel.comm_manager.register_target("meshcat", (comm, message) => {{
        comm.on_msg(function(msg) {{
            viewer.handle_command(msg.content.data)
        }});
    }});
    console.log("ready for meshcat comms");
</script>' style="height: 420px; width: 100%; border: none">
"""))
                # TODO(russt): Make this more robust.  jupyter requires me to put meshcat into an iframe, which defers the loading.  I have not yet figured out a good way to block on the iframe load nor avoid the iframe altogether.  
                time.sleep(1)  # Conservative wait for iframe to load.
                self.channel = comm.Comm(target_name="meshcat")

    @staticmethod
    def view_into(path, channel):
        vis = JupyterVisualizer(write_html=False)
        vis.path = path
        vis.channel = channel
        return vis

    def __getitem__(self, path):
        return JupyterVisualizer.view_into(self.path.append(path), self.channel)

    def _send(self, command):
        # TODO(russt): Clean this up to use one channel, many messages, pending any resolution to https://stackoverflow.com/questions/63263921/is-there-a-way-to-register-a-message-handler-callback-on-a-google-colab-kernel-c
        if running_in_colab:
            comm.Comm(target_name="meshcat", data=command.lower())
        else:
            self.channel.send(data=command.lower())

    def set_object(self, geometry, material=None):
        return self._send(SetObject(geometry, material, self.path))

    def set_transform(self, matrix=np.eye(4)):
        return self._send(SetTransform(matrix, self.path))

    def set_property(self, key, value):
        return self._send(SetProperty(key, value, self.path))

    def set_animation(self, animation, play=True, repetitions=1):
        return self._send(SetAnimation(animation, play=play,        
                          repetitions=repetitions))

    def delete(self):
        return self._send(Delete(self.path))
