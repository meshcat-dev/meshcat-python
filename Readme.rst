meshcat-python: Python Bindings to the MeshCat WebGL viewer
===========================================================

.. image:: https://travis-ci.org/rdeits/meshcat-python.svg?branch=master
    :target: https://travis-ci.org/rdeits/meshcat-python
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

Using pip:

::

	pip install meshcat

From source:

::

	git clone https://github.com/rdeits/meshcat-python
	cd meshcat-python
	python setup.py install

You will need the ZeroMQ libraries installed on your system:

Ubuntu/Debian:

::

	apt-get install libzmq3

Homebrew:

::

	brew install zmq

Usage
-----

For examples of interactive usage, see demo.ipynb_

.. _demo.ipynb: demo.ipynb


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

A viewer message consists of a single ZeroMQ message containing a msgpack_ encoded dictionary. The format of the message is:

::

	{
		"commands": [
			{
				"type": "set_object",         // one of set_object, set_transform, or delete
				"path": ["meshcat", "box1"],  // the path of the object
				"object": <three.js JSON>
			},
			{
				"type": "set_transform",
				"path": ["meshcat", "box2"],
				"matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
			}, 
			{
				"type": "delete",
				"path", ["meshcat", "box3"]
			}
		]
	}

The format of the ``object`` field is exactly the built-in JSON serialization format from three.js (note that we use the JSON structure, but actually use msgpack for the encoding due to its much better performance). For examples of the JSON structure, see the `three.js wiki`_. 

The format of the ``matrix`` in a ``set_transform`` command is a column-major homogeneous transformation matrix. 

.. _msgpack: https://msgpack.org/index.html
.. _wiki: https://github.com/mrdoob/three.js/wiki/JSON-Geometry-format-4

Packing Arrays
--------------

Msgpack's default behavior is not ideal for packing large contiguous arrays (it inserts a type code before every element). For faster transfer of large pointclouds and meshes, msgpack ``Ext`` codes are available for several types of arrays. For the full list, see https://github.com/kawanet/msgpack-lite#extension-types . The ``meshcat`` Python bindings will automatically use these ``Ext`` types for ``numpy`` array inputs. 

