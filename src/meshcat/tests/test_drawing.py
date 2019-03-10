from __future__ import absolute_import, division, print_function

import unittest
import subprocess
import sys
import os

if sys.version_info >= (3, 0):
    from io import StringIO, BytesIO
else:
    from StringIO import StringIO
    BytesIO = StringIO

import io

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
        v["cube"].set_object(g.Box([1.0, 0.2, 0.3]))
        v["cube"].delete()
        v["cube"].set_object(g.Box([0.1, 0.2, 0.3]))
        v["cube"].set_transform(tf.translation_matrix([0.05, 0.1, 0.15]))
        v["cylinder"].set_object(g.Cylinder(0.2, 0.1), g.MeshLambertMaterial(color=0x22dd22))
        v["cylinder"].set_transform(tf.translation_matrix([0, 0.5, 0.1]).dot(tf.rotation_matrix(-np.pi / 2, [1, 0, 0])))
        v["sphere"].set_object(g.Mesh(g.Sphere(0.15), g.MeshLambertMaterial(color=0xff11dd)))
        v["sphere"].set_transform(tf.translation_matrix([0, 1, 0.15]))
        v["ellipsoid"].set_object(g.Ellipsoid([0.3, 0.1, 0.1]))
        v["ellipsoid"].set_transform(tf.translation_matrix([0, 1.5, 0.1]))

        v["transparent_ellipsoid"].set_object(g.Mesh(
            g.Ellipsoid([0.3, 0.1, 0.1]),
            g.MeshLambertMaterial(color=0xffffff,
                                  opacity=0.5)))
        v["transparent_ellipsoid"].set_transform(tf.translation_matrix([0, 2.0, 0.1]))

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

        v = self.vis["meshes/convex"]
        v["obj"].set_object(g.Mesh(g.ObjMeshGeometry.from_file(os.path.join(meshcat.viewer_assets_path(), "../tests/data/mesh_0_convex_piece_0.obj"))))
        v["stl_ascii"].set_object(g.Mesh(g.StlMeshGeometry.from_file(os.path.join(meshcat.viewer_assets_path(), "../tests/data/mesh_0_convex_piece_0.stl_ascii"))))
        v["stl_ascii"].set_transform(tf.translation_matrix([0, -0.5, 0]))
        v["stl_binary"].set_object(g.Mesh(g.StlMeshGeometry.from_file(os.path.join(meshcat.viewer_assets_path(), "../tests/data/mesh_0_convex_piece_0.stl_binary"))))
        v["stl_binary"].set_transform(tf.translation_matrix([0, -1, 0]))
        v["dae"].set_object(g.Mesh(g.DaeMeshGeometry.from_file(os.path.join(meshcat.viewer_assets_path(), "../tests/data/mesh_0_convex_piece_0.dae"))))
        v["dae"].set_transform(tf.translation_matrix([0, -1.5, 0]))


        v = self.vis["points"]
        v.set_transform(tf.translation_matrix([-1, 0, 0]))
        verts = np.random.rand(3, 100000)
        colors = verts
        v["random"].set_object(g.PointCloud(verts, colors))
        v["random"].set_transform(tf.translation_matrix([-0.5, -0.5, 0]))

    def test_mesh_stream(self):
        """ Applications using meshcat may already have meshes loaded in memory. It is
        more efficient to load these meshes with streams rather than going to and then
        from a file on disk. To test this we are importing meshes from disk and 
        converting them into streams so it kind of defeats the intended purpose! But at
        least it tests the functionality.
        """
        self.vis.delete()
        v = self.vis["meshes/convex"]

        # Obj file
        filename = os.path.join(meshcat.viewer_assets_path(),
                                "../tests/data/mesh_0_convex_piece_0.obj")
        with open(filename, "r") as f:
            fio = StringIO(f.read())
            v["stream_obj"].set_object(g.Mesh(g.ObjMeshGeometry.from_stream(fio)))
            v["stream_stl_ascii"].set_transform(tf.translation_matrix([0, 0.0, 0]))

        # STL ASCII
        filename = os.path.join(meshcat.viewer_assets_path(),
                                "../tests/data/mesh_0_convex_piece_0.stl_ascii")
        with open(filename, "r") as f:
            fio = StringIO(f.read())
            v["stream_stl_ascii"].set_object(g.Mesh(g.StlMeshGeometry.from_stream(fio)))
            v["stream_stl_ascii"].set_transform(tf.translation_matrix([0, -0.5, 0]))

        # STL Binary
        filename = os.path.join(meshcat.viewer_assets_path(),
                                "../tests/data/mesh_0_convex_piece_0.stl_binary")
        with open(filename, "rb") as f:
            fio = BytesIO(f.read())
            v["stream_stl_binary"].set_object(g.Mesh(g.StlMeshGeometry.from_stream(fio)))
            v["stream_stl_binary"].set_transform(tf.translation_matrix([0, -1.0, 0]))

        # DAE
        filename = os.path.join(meshcat.viewer_assets_path(),
                                "../tests/data/mesh_0_convex_piece_0.dae")
        with open(filename, "r") as f:
            fio = StringIO(f.read())
            v["stream_dae"].set_object(g.Mesh(g.DaeMeshGeometry.from_stream(fio)))
            v["stream_dae"].set_transform(tf.translation_matrix([0, -1.5, 0]))


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


class TestAnimation(VisualizerTest):
    def runTest(self):
        v = self.vis["shapes"]
        v.set_transform(tf.translation_matrix([1., 0, 0]))
        v["cube"].set_object(g.Box([0.1, 0.2, 0.3]))

        animation = meshcat.animation.Animation()
        with animation.at_frame(v, 0) as frame_vis:
            frame_vis.set_transform(tf.translation_matrix([0, 0, 0]))
        with animation.at_frame(v, 30) as frame_vis:
            frame_vis.set_transform(tf.translation_matrix([2, 0, 0]).dot(tf.rotation_matrix(np.pi/2, [0, 0, 1])))
        v.set_animation(animation)


class TestCameraAnimation(VisualizerTest):
    def runTest(self):
        v = self.vis["shapes"]
        v.set_transform(tf.translation_matrix([1., 0, 0]))
        v["cube"].set_object(g.Box([0.1, 0.2, 0.3]))

        animation = meshcat.animation.Animation()
        with animation.at_frame(v, 0) as frame_vis:
            frame_vis.set_transform(tf.translation_matrix([0, 0, 0]))
        with animation.at_frame(v, 30) as frame_vis:
            frame_vis.set_transform(tf.translation_matrix([2, 0, 0]).dot(tf.rotation_matrix(np.pi/2, [0, 0, 1])))
        with animation.at_frame(v, 0) as frame_vis:
            frame_vis["/Cameras/default/rotated/<object>"].set_property("zoom", "number", 1)
        with animation.at_frame(v, 30) as frame_vis:
            frame_vis["/Cameras/default/rotated/<object>"].set_property("zoom", "number", 0.5)
        v.set_animation(animation)
