from __future__ import absolute_import, division, print_function

import unittest
import subprocess
import sys
import os

import numpy as np

import meshcat
import meshcat.geometry as g
import meshcat.transformations as tf


class VisualizerTest(unittest.TestCase):
    def setUp(self):
        self.vis = meshcat.Visualizer()

        if "CI" in os.environ:
            port = self.vis.url().split(":")[-1].split("/")[0]
            self.dummy_proc = subprocess.Popen([sys.executable, "-m", "meshcat.tests.dummy_websocket_client", str(port)])
        else:
            self.vis.open()
            self.dummy_proc = None

        self.vis.wait()

    def tearDown(self):
        if self.dummy_proc is not None:
            self.dummy_proc.kill()


class TestDrawing(VisualizerTest):
    def runTest(self):
        self.vis.delete()
        v = self.vis["shapes"]
        v.set_transform(tf.translation_matrix([1., 0, 0]))
        v["cube"].set_object(g.Box([0.1, 0.2, 0.3]))
        v["cube"].set_transform(tf.translation_matrix([0.05, 0.1, 0.15]))
        v["cylinder"].set_object(g.Cylinder(0.2, 0.1), g.MeshLambertMaterial(color=0x22dd22))
        v["cylinder"].set_transform(tf.translation_matrix([0, 0.5, 0.1]).dot(tf.rotation_matrix(-np.pi / 2, [1, 0, 0])))
        v["sphere"].set_object(g.Mesh(g.Sphere(0.15), g.MeshLambertMaterial(color=0xff11dd)))
        v["sphere"].set_transform(tf.translation_matrix([0, 1, 0.15]))
        v["ellipsoid"].set_object(g.Ellipsoid([0.3, 0.1, 0.1]))
        v["ellipsoid"].set_transform(tf.translation_matrix([0, 1.5, 0.1]))

        v = self.vis["meshes/valkyrie/head"]
        v.set_object(g.Mesh(
            g.ObjMeshGeometry.from_file(os.path.join(meshcat.viewer_assets_path(), "data/head_multisense.obj")),
            g.MeshLambertMaterial(
                map=g.ImageTexture(
                    image=g.PngImage.from_file(os.path.join(meshcat.viewer_assets_path(), "data/HeadTextureMultisense.png"))
                )
            )
        ))
        v.set_transform(tf.translation_matrix([0, 0.5, 0.5]))

        v = self.vis["points"]
        v.set_transform(tf.translation_matrix([-1, 0, 0]))
        verts = np.random.rand(3, 100000)
        colors = verts
        v["random"].set_object(g.PointCloud(verts, colors))
        v["random"].set_transform(tf.translation_matrix([-0.5, -0.5, 0]))


class TestStandaloneServer(unittest.TestCase):
    def setUp(self):
        self.zmq_url = "tcp://127.0.0.1:5560"
        args = ["meshcat-server", "--zmq-url", self.zmq_url]

        if "CI" not in os.environ:
            args.append("--open")

        self.server_proc = subprocess.Popen(args)
        self.vis = meshcat.Visualizer(self.zmq_url)
        # self.vis = meshcat.Visualizer()
        # self.vis.open()

        if "CI" in os.environ:
            port = self.vis.url().split(":")[-1].split("/")[0]
            self.dummy_proc = subprocess.Popen([sys.executable, "-m", "meshcat.tests.dummy_websocket_client", str(port)])
        else:
            # self.vis.open()
            self.dummy_proc = None

        self.vis.wait()

    def runTest(self):
        v = self.vis["shapes"]
        v["cube"].set_object(g.Box([0.1, 0.2, 0.3]))
        v.set_transform(tf.translation_matrix([1., 0, 0]))
        v.set_transform(tf.translation_matrix([1., 1., 0]))

    def tearDown(self):
        if self.dummy_proc is not None:
            self.dummy_proc.kill()
        self.server_proc.kill()

