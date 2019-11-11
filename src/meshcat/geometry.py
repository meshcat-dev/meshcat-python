from __future__ import absolute_import, division, print_function

import sys
import base64
import uuid

if sys.version_info >= (3, 0):
    unicode = str
    from io import StringIO, BytesIO
else:
    from StringIO import StringIO
    BytesIO = StringIO


import umsgpack
import numpy as np

from . import transformations as tf


class SceneElement(object):
    def __init__(self):
        self.uuid = unicode(uuid.uuid1())


class ReferenceSceneElement(SceneElement):
    def lower_in_object(self, object_data):
        object_data.setdefault(self.field, []).append(self.lower(object_data))
        return self.uuid


class Geometry(ReferenceSceneElement):
    field = "geometries"

    def intrinsic_transform(self):
        return tf.identity_matrix()


class Material(ReferenceSceneElement):
    field = "materials"


class Texture(ReferenceSceneElement):
    field = "textures"


class Image(ReferenceSceneElement):
    field = "images"


class Box(Geometry):
    def __init__(self, lengths):
        super(Box, self).__init__()
        self.lengths = lengths

    def lower(self, object_data):
        return {
            u"uuid": self.uuid,
            u"type": u"BoxGeometry",
            u"width": self.lengths[0],
            u"height": self.lengths[1],
            u"depth": self.lengths[2]
        }


class Sphere(Geometry):
    def __init__(self, radius):
        super(Sphere, self).__init__()
        self.radius = radius

    def lower(self, object_data):
        return {
            u"uuid": self.uuid,
            u"type": u"SphereGeometry",
            u"radius": self.radius,
            u"widthSegments" : 20,
            u"heightSegments" : 20
        }


class Ellipsoid(Sphere):
    """
    An Ellipsoid is treated as a Sphere of unit radius, with an affine
    transformation applied to distort it into the ellipsoidal shape
    """
    def __init__(self, radii):
        super(Ellipsoid, self).__init__(1.0)
        self.radii = radii

    def intrinsic_transform(self):
        return np.diag(np.hstack((self.radii, 1.0)))


"""
A cylinder of the given height and radius. By Three.js convention, the axis of
rotational symmetry is aligned with the y-axis.
"""
class Cylinder(Geometry):
    def __init__(self, height, radius=1.0, radiusTop=None, radiusBottom=None):
        super(Cylinder, self).__init__()
        if radiusTop is not None and radiusBottom is not None:
            self.radiusTop = radiusTop
            self.radiusBottom = radiusBottom
        else:
            self.radiusTop = radius
            self.radiusBottom = radius
        self.height = height
        self.radialSegments = 50

    def lower(self, object_data):
        return {
            u"uuid": self.uuid,
            u"type": u"CylinderGeometry",
            u"radiusTop": self.radiusTop,
            u"radiusBottom": self.radiusBottom,
            u"height": self.height,
            u"radialSegments": self.radialSegments
        }


class MeshMaterial(Material):
    def __init__(self, color=0xffffff, reflectivity=0.5, map=None,
                 side = 2, transparent = None, opacity = 1.0, **kwargs):
        super(MeshMaterial, self).__init__()
        self.color = color
        self.reflectivity = reflectivity
        self.map = map
        self.properties = kwargs
        self.side = side
        self.transparent = transparent
        self.opacity = opacity

    def lower(self, object_data):
        # Three.js allows a material to have an opacity which is != 1,
        # but to still be non-transparent, in which case the opacity only
        # serves to desaturate the material's color. That's a pretty odd
        # combination of things to want, so by default we juse use the
        # opacity value to decide whether to set transparent to True or
        # False.
        if self.transparent is None:
            transparent = bool(self.opacity != 1)
        else:
            transparent = self.transparent
        data = {
            u"uuid": self.uuid,
            u"type": self._type,
            u"color": self.color,
            u"reflectivity": self.reflectivity,
            u"side": self.side,
            u"transparent": transparent,
            u"opacity": self.opacity
        }
        data.update(self.properties)
        if self.map is not None:
            data[u"map"] = self.map.lower_in_object(object_data)
        return data


class MeshBasicMaterial(MeshMaterial):
    _type=u"MeshBasicMaterial"


class MeshPhongMaterial(MeshMaterial):
    _type=u"MeshPhongMaterial"


class MeshLambertMaterial(MeshMaterial):
    _type=u"MeshLambertMaterial"


class MeshToonMaterial(MeshMaterial):
    _type=u"MeshToonMaterial"


class PngImage(Image):
    def __init__(self, data):
        super(PngImage, self).__init__()
        self.data = data

    @staticmethod
    def from_file(fname):
        with open(fname, "rb") as f:
            return PngImage(f.read())

    def lower(self, object_data):
        return {
            u"uuid": self.uuid,
            u"url": unicode("data:image/png;base64," + base64.b64encode(self.data).decode('ascii'))
        }


class GenericTexture(Texture):
    def __init__(self, properties):
        super(GenericTexture, self).__init__()
        self.properties = properties

    def lower(self, object_data):
        data = {u"uuid": self.uuid}
        data.update(self.properties)
        if u"image" in data:
            image = data[u"image"]
            data[u"image"] = image.lower_in_object(object_data)
        return data


class ImageTexture(Texture):
    def __init__(self, image, wrap=[1001, 1001], repeat=[1, 1], **kwargs):
        super(ImageTexture, self).__init__()
        self.image = image
        self.wrap = wrap
        self.repeat = repeat
        self.properties = kwargs

    def lower(self, object_data):
        data = {
            u"uuid": self.uuid,
            u"wrap": self.wrap,
            u"repeat": self.repeat,
            u"image": self.image.lower_in_object(object_data)
        }
        data.update(self.properties)
        return data


class GenericMaterial(Material):
    def __init__(self, properties):
        self.properties = properties
        self.uuid = str(uuid.uuid1())

    def lower(self, object_data):
        data = {u"uuid": self.uuid}
        data.update(self.properties)
        if u"map" in data:
            texture = data[u"map"]
            data[u"map"] = texture.lower_in_object(object_data)
        return data


class Object(SceneElement):
    def __init__(self, geometry, material=MeshPhongMaterial()):
        super(Object, self).__init__()
        self.geometry = geometry
        self.material = material

    def lower(self):
        data = {
            u"metadata": {
                u"version": 4.5,
                u"type": u"Object",
            },
            u"geometries": [],
            u"materials": [],
            u"object": {
                u"uuid": self.uuid,
                u"type": self._type,
                u"geometry": self.geometry.uuid,
                u"material": self.material.uuid,
                u"matrix": list(self.geometry.intrinsic_transform().flatten())
            }
        }
        self.geometry.lower_in_object(data)
        self.material.lower_in_object(data)
        return data


class Mesh(Object):
    _type = u"Mesh"


def item_size(array):
    if array.ndim == 1:
        return 1
    elif array.ndim == 2:
        return array.shape[0]
    else:
        raise ValueError("I can only pack 1- or 2-dimensional numpy arrays, but this one has {:d} dimensions".format(array.ndim))


def threejs_type(dtype):
    if dtype == np.uint8:
        return u"Uint8Array", 0x12
    elif dtype == np.int32:
        return u"Int32Array", 0x15
    elif dtype == np.uint32:
        return u"Uint32Array", 0x16
    elif dtype == np.float32:
        return u"Float32Array", 0x17
    else:
        raise ValueError("Unsupported datatype: " + str(dtype))


def pack_numpy_array(x):
    if x.dtype == np.float64:
        x = x.astype(np.float32)
    typename, extcode = threejs_type(x.dtype)
    return {
        u"itemSize": item_size(x),
        u"type": typename,
        u"array": umsgpack.Ext(extcode, x.tobytes('F')),
        u"normalized": False
    }


def data_from_stream(stream):
    if sys.version_info >= (3, 0):
        if isinstance(stream, BytesIO):
            data = stream.read().decode(encoding='utf-8')
        elif isinstance(stream, StringIO):
            data = stream.read()
        else:
            raise ValueError('Stream must be instance of StringIO or BytesIO, not {}'.format(type(stream)))
    else:
        data = stream.read()
    return data


class MeshGeometry(Geometry):
    def __init__(self, contents, mesh_format):
        super(MeshGeometry, self).__init__()
        self.contents = contents
        self.mesh_format = mesh_format

    def lower(self, object_data):
        return {
            u"type": u"_meshfile",
            u"uuid": self.uuid,
            u"format": self.mesh_format,
            u"data": self.contents
        }


class ObjMeshGeometry(MeshGeometry):
    def __init__(self, contents):
        super(ObjMeshGeometry, self, contents, u"obj").__init__()

    @staticmethod
    def from_file(fname):
        with open(fname, "r") as f:
            return MeshGeometry(f.read(), u"obj")

    @staticmethod
    def from_stream(f):
        return MeshGeometry(data_from_stream(f), u"obj")


class DaeMeshGeometry(MeshGeometry):
    def __init__(self, contents):
        super(DaeMeshGeometry, self, contents, u"dae").__init__()

    @staticmethod
    def from_file(fname):
        with open(fname, "r") as f:
            return MeshGeometry(f.read(), u"dae")

    @staticmethod
    def from_stream(f):
        return MeshGeometry(data_from_stream(f), u"dae")


class StlMeshGeometry(MeshGeometry):
    def __init__(self, contents):
        super(StlMeshGeometry, self, contents, u"stl").__init__()

    @staticmethod
    def from_file(fname):
        with open(fname, "rb") as f:
            arr = np.frombuffer(f.read(), dtype=np.uint8)
            _, extcode = threejs_type(np.uint8)
            encoded = umsgpack.Ext(extcode, arr.tobytes())
            return MeshGeometry(encoded, u"stl")

    @staticmethod
    def from_stream(f):
        if sys.version_info >= (3, 0):
            if isinstance(f, BytesIO):
                arr  = np.frombuffer(f.read(), dtype=np.uint8)
            elif isinstance(f, StringIO):
                arr = np.frombuffer(bytes(f.read(), "utf-8"), dtype=np.uint8)
            else:
                raise ValueError('Stream must be instance of StringIO or BytesIO, not {}'.format(type(f)))
        else:
            arr  = np.frombuffer(f.read(), dtype=np.uint8)
        _, extcode = threejs_type(np.uint8)
        encoded = umsgpack.Ext(extcode, arr.tobytes())
        return MeshGeometry(encoded, u"stl")


class PointsGeometry(Geometry):
    def __init__(self, position, color=None):
        super(PointsGeometry, self).__init__()
        self.position = position
        self.color = color

    def lower(self, object_data):
        attrs = {u"position": pack_numpy_array(self.position)}
        if self.color is not None:
            attrs[u"color"] = pack_numpy_array(self.color)
        return {
            u"uuid": self.uuid,
            u"type": u"BufferGeometry",
            u"data": {
                u"attributes": attrs
            }
        }


class PointsMaterial(Material):
    def __init__(self, size=0.001, color=0xffffff):
        super(PointsMaterial, self).__init__()
        self.size = size
        self.color = color

    def lower(self, object_data):
        return {
            u"uuid": self.uuid,
            u"type": u"PointsMaterial",
            u"color": self.color,
            u"size": self.size,
            u"vertexColors": 2
        }


class Points(Object):
    _type = u"Points"


def PointCloud(position, color, **kwargs):
    return Points(
        PointsGeometry(position, color),
        PointsMaterial(**kwargs)
    )


class Line(Object):
    _type = u"Line"


class LineSegments(Object):
    _type = u"LineSegments"


class LineLoop(Object):
    _type = u"LineLoop"
