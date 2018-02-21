import asyncio
import threading

import websockets
import zmq
import zmq.asyncio

from . import fileserver
from .fileserver import find_available_port

# Tell asyncio to use zmq's eventloop. Future
# versions may not need this. See:
# https://github.com/zeromq/pyzmq/issues/1034#issuecomment-315113731
zmq.asyncio.install()

loop = asyncio.get_event_loop()

DEFAULT_WEBSOCKET_PORT = 5000
DEFAULT_ZMQ_HOST = "tcp://127.0.0.1"
DEFAULT_ZMQ_PORT = 6000
MAX_ATTEMPTS = 1000

class ZMQWebSocketBridge:
    def __init__(self, host="127.0.0.1", zmq_url=None, websocket_port=None):
        self.queues = set()
        self.host = host

        if websocket_port is None:
            find_available_port(self.serve_websockets, DEFAULT_WEBSOCKET_PORT, MAX_ATTEMPTS)
        else:
            self.serve_websockets(websocket_port)

        if zmq_url is None:
            find_available_port(
                lambda port: self.connect_zmq("{:s}:{:d}".format(DEFAULT_ZMQ_HOST, port)), DEFAULT_ZMQ_PORT, MAX_ATTEMPTS)
        else:
            self.connect_zmq(zmq_url)

    async def handle_new_connection(websocket, path):
        print("connected", websocket)
        my_queue = asyncio.Queue()
        self.queues.add(my_queue)
        try:
            while True:
                msg = await my_queue.get()
                await websocket.send(msg)
                my_queue.task_done()
        except websockets.ConnectionClosed as e:
            self.queues.remove(queue)

    def serve_websockets(self, port):
        start_server = websockets.serve(self.handle_new_connection, self.host, port)
        self.websocket_server = loop.run_until_complete(start_server)
        self.websocket_port = port
        print("Serving websockets at ws://{:s}:{:d}".format(self.host, self.websocket_port))

    def connect_zmq(self, url):
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(url)
        self.zmq_url = url
        print("ZMQ socket bound to {:s}".format(self.zmq_url))

    async def run(self):
        while True:
            message = await self.socket.recv()
            await asyncio.wait([q.put(message) for q in self.queues])
            await self.socket.send(b"ok")


class ZMQServer:
    def __init__(self, host="127.0.0.1", zmq_url=None, websocket_port=None, fileserver_port=None):
        self.bridge = ZMQWebSocketBridge(host=host, zmq_url=zmq_url, websocket_port=websocket_port)
        self.fileserver_thread, self.fileserver_port = fileserver.run_threaded(host=host, port=fileserver_port)

    async def run(self):
        await self.bridge.run()

    def run_sync(self):
        loop.run_until_complete(self.run())

    def run_threaded(self):
        thread = threading.Thread(target=self.run_sync, daemon=True)

# async def run_zmq():
#     while True:
#         message = await socket.recv()
#         for q in queues:
#             await q.put(message)
#         await socket.send(b"ok")

if __name__ == '__main__':
    server = ZMQServer()
    server.run_sync()
