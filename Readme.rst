meshcat-python: Python Bindings to the MeshCat WebGL viewer
===========================================================

.. image:: https://github.com/rdeits/meshcat-python/workflows/CI/badge.svg?branch=master
    :target: https://github.com/rdeits/meshcat-python/actions?query=workflow%3ACI
.. image:: https://codecov.io/gh/rdeits/meshcat-python/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/rdeits/meshcat-python


MeshCat_ is a remotely-controllable 3D viewer, built on top of three.js_. The viewer contains a tree of objects and transformations (i.e. a scene graph) and allows those objects and transformations to be added and manipulated with simple commands. This makes it easy to create 3D visualizations of geometries, mechanisms, and robots. 

The MeshCat architecture is based on the model used by Jupyter_:

- The viewer itself runs entirely in the browser, with no external dependencies
- The MeshCat server communicates with the viewer via WebSockets
- Your code can use the meshcat python libraries or communicate directly with the server through its ZeroMQ_ socket. 

.. _ZeroMQ: http://zguide.zeromq.org/
.. _Jupyter: http://jupyter.org/
.. _MeshCat: https://github.com/rdeits/meshcat
.. _three.js: https://threejs.org/

Installation
------------

The latest version of MeshCat requires Python 3.6 or above.

Using pip:

::

    pip install meshcat

From source:

::

    git clone https://github.com/rdeits/meshcat-python
    git submodule update --init --recursive
    cd meshcat-python
    python setup.py install

You will need the ZeroMQ libraries installed on your system:

Ubuntu/Debian:

::

    apt install libzmq3-dev

Homebrew:

::

    brew install zmq

Windows:

Download the official installer from zeromq.org_.

.. _zeromq.org: https://zeromq.org/download/

Usage
=====

For examples of interactive usage, see demo.ipynb_

.. _demo.ipynb: examples/demo.ipynb

Under the Hood
==============

Starting a Server
-----------------

If you want to run your own meshcat server (for example, to communicate with the viewer over ZeroMQ from another language), all you need to do is run:

::

    meshcat-server

The server will choose an available ZeroMQ URL and print that URL over stdout. If you want to specify a URL, just do:

::

    meshcat-server --zmq-url=<your URL>

You can also instruct the server to open a browser window with:

::

    meshcat-server --open

Protocol
--------

All communication with the meshcat server happens over the ZMQ socket. Some commands consist of multiple ZMQ frames. 

:ZMQ frames:
    ``["url"]``
:Action:
    Request URL
:Response:
    The web URL for the server. Open this URL in your browser to see the 3D scene.

|	

:ZMQ frames:
    ``["wait"]``
:Action:
    Wait for a browser to connect
:Response:
    "ok" when a brower has connected to the server. This is useful in scripts to block execution until geometry can actually be displayed.
    
|

:ZMQ frames:
    ``["set_object", "/slash/separated/path", data]``
:Action:
    Set the object at the given path. ``data`` is a ``MsgPack``-encoded dictionary, described below. 
:Response:
    "ok"

|

:ZMQ frames:
    ``["set_transform", "/slash/separated/path", data]``
:Action:
    Set the transform of the object at the given path. There does not need to be any geometry at that path yet, so ``set_transform`` and ``set_object`` can happen in any order. ``data`` is a ``MsgPack``-encoded dictionary, described below. 
:Response:
    "ok"

|

:ZMQ frames:
    ``["delete", "/slash/separated/path", data]``
:Action:
    Delete the object at the given path. ``data`` is a ``MsgPack``-encoded dictionary, described below. 
:Response:
    "ok"

|

``set_object`` data format
^^^^^^^^^^^^^^^^^^^^^^^^^^
::

    {
        "type": "set_object",
        "path": "/slash/separated/path",  // the path of the object
        "object": <three.js JSON>
    }

The format of the ``object`` field is exactly the built-in JSON serialization format from three.js (note that we use the JSON structure, but actually use msgpack for the encoding due to its much better performance). For examples of the JSON structure, see the three.js wiki_ . 

Note on redundancy
    The ``type`` and ``path`` fields are duplicated: they are sent once in the first two ZeroMQ frames and once inside the MsgPack-encoded data. This is intentional and makes it easier for the server to handle messages without unpacking them fully. 

.. _wiki: https://github.com/mrdoob/three.js/wiki/JSON-Geometry-format-4
.. _msgpack: https://msgpack.org/index.html

``set_transform`` data format
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

    {
        "type": "set_transform",
        "path": "/slash/separated/path",
        "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    }

The format of the ``matrix`` in a ``set_transform`` command is a column-major homogeneous transformation matrix. 

``delete`` data format
^^^^^^^^^^^^^^^^^^^^^^
::

    {
        "type": "delete",
        "path", "/slash/separated/path"
    }

Examples
--------

Creating a box at path ``/meshcat/box``

::

    {
        "type": "set_object",
        "path": "/meshcat/box",
        "object": {
            "metadata": {"type": "Object", "version": 4.5},
            "geometries": [{"depth": 0.5,
                            "height": 0.5,
                            "type": "BoxGeometry",
                            "uuid": "fbafc3d6-18f8-11e8-b16e-f8b156fe4628",
                            "width": 0.5}],
            "materials": [{"color": 16777215,
                           "reflectivity": 0.5,
                           "type": "MeshPhongMaterial",
                           "uuid": "e3c21698-18f8-11e8-b16e-f8b156fe4628"}],
            "object": {"geometry": "fbafc3d6-18f8-11e8-b16e-f8b156fe4628",
                       "material": "e3c21698-18f8-11e8-b16e-f8b156fe4628",
                       "matrix": [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                       "type": "Mesh",
                       "uuid": "fbafc3d7-18f8-11e8-b16e-f8b156fe4628"}},
    }

Translating that box by the vector ``[2, 3, 4]``:

::

    {
        "type": "set_transform",
        "path": "/meshcat/box",
        "matrix": [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 2.0, 3.0, 4.0, 1.0]
    }

Packing Arrays
--------------

Msgpack's default behavior is not ideal for packing large contiguous arrays (it inserts a type code before every element). For faster transfer of large pointclouds and meshes, msgpack ``Ext`` codes are available for several types of arrays. For the full list, see https://github.com/kawanet/msgpack-lite#extension-types . The ``meshcat`` Python bindings will automatically use these ``Ext`` types for ``numpy`` array inputs. 


