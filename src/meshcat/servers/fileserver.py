import http.server
from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
import socketserver
import os
import threading

viewer_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "viewer", "static"))

DEFAULT_FILESERVER_PORT = 7000
MAX_ATTEMPTS = 1000


# https://stackoverflow.com/a/46332163
class ViewerFileRequestHandler(SimpleHTTPRequestHandler):
    """This handler uses server.base_path instead of always using os.getcwd()"""
    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(viewer_root, relpath)
        return fullpath

    def log_message(self, *args):
        pass


def find_available_port(func, default_port, max_attempts=MAX_ATTEMPTS):
    for i in range(max_attempts):
        port = default_port + i
        try:
            return func(port), port
        except OSError as e:
            print("Port: {:d} in use, trying another...".format(port))
            pass
    else:
        raise(Exception("Could not find an available port in the range: [{:d}, {:d})".format(default_port, max_attempts + default_port)))


def start_fileserver(host="127.0.0.1", port=None):
    if port is None:
        httpd, port = find_available_port(
            lambda port: socketserver.TCPServer((host, port), ViewerFileRequestHandler),
            DEFAULT_FILESERVER_PORT)
    else:
        httpd = socketserver.TCPServer((host, port), ViewerFileRequestHandler)
    print("Serving files at {:s}:{:d}".format(host, port))
    return httpd, port


def run_threaded(*args, **kwargs):
    httpd, port = start_fileserver(*args, **kwargs)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return thread, port
