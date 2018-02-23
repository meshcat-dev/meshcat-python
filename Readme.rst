.. image:: https://travis-ci.org/rdeits/meshcat-python.svg?branch=master
    :target: https://travis-ci.org/rdeits/meshcat-python
.. image:: https://codecov.io/gh/rdeits/meshcat-python/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/rdeits/meshcat-python


Introduction
============

MeshCat_ is a remotely-controllable 3D viewer, built on top of three.js_. The MeshCat viewer runs in a browser and listens for geometry commands over WebSockets. This makes it easy to create a tree of objects and transformations by sending the appropriate commands over the websocket.

.. _MeshCat: https://github.com/rdeits/meshcat
.. _three.js: https://threejs.org/

This package, meshcat-python, allows you to create objects and move them in space from Python. For some examples of usage, see `demo.ipynb`.
