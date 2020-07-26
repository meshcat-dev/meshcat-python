from __future__ import absolute_import, division, print_function

import unittest

from meshcat.servers.zmqserver import StartZmqServerAsSubprocess

class TestStartZmqServer(unittest.TestCase):
    """
    Test the StartZmqServerAsSubprocess method.
    """

    def test_default_args(self):
        proc, zmq_url, web_url = StartZmqServerAsSubprocess()
        self.assertIn("127.0.0.1", web_url)

    def test_ngrok(self):
        proc, zmq_url, web_url = StartZmqServerAsSubprocess( server_args=["--ngrok_http_tunnel"])
        self.assertNotIn("127.0.0.1", web_url)
