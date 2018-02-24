from __future__ import absolute_import, division, print_function

import base64
import uuid

import umsgpack
import numpy as np

from . import transformations as tf


class SceneElement(object):
    def __init__(self):
        self.uuid = str(uuid.uuid1())


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
            "uuid": self.uuid,
            "type": "BoxGeometry",
            "width": self.lengths[0],
            "height": self.lengths[1],
            "depth": self.lengths[2]
        }


class Sphere(Geometry):
    def __init__(self, radius):
        super(Sphere, self).__init__()
        self.radius = radius

    def lower(self, object_data):
        return {
            "uuid": self.uuid,
            "type": "SphereGeometry",
            "radius": self.radius,
            "widthSegments" : 20,
            "heightSegments" : 20
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
            "uuid": self.uuid,
            "type": "CylinderGeometry",
            "radiusTop": self.radiusTop,
            "radiusBottom": self.radiusBottom,
            "height": self.height,
            "radialSegments": self.radialSegments
        }


class MeshMaterial(Material):
    def __init__(self, color=0xffffff, reflectivity=0.5, map=None, **kwargs):
        super(MeshMaterial, self).__init__()
        self.color = color
        self.reflectivity = reflectivity
        self.map = map
        self.properties = kwargs

    def lower(self, object_data):
        data = {
            "uuid": self.uuid,
            "type": self._type,
            "color": self.color,
            "reflectivity": self.reflectivity,
        }
        data.update(self.properties)
        if self.map is not None:
            data["map"] = self.map.lower_in_object(object_data)
        return data


class MeshBasicMaterial(MeshMaterial):
    _type="MeshBasicMaterial"


class MeshPhongMaterial(MeshMaterial):
    _type="MeshPhongMaterial"


class MeshLambertMaterial(MeshMaterial):
    _type="MeshLambertMaterial"


class MeshToonMaterial(MeshMaterial):
    _type="MeshToonMaterial"


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
            "uuid": self.uuid,
            "url": "data:image/png;base64," + base64.b64encode(self.data).decode('ascii')
        }


class GenericTexture(Texture):
    def __init__(self, properties):
        super(GenericTexture, self).__init__()
        self.properties = properties

    def lower(self, object_data):
        data = {"uuid": self.uuid}
        data.update(self.properties)
        if "image" in data:
            image = data["image"]
            data["image"] = image.lower_in_object(object_data)
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
            "uuid": self.uuid,
            "wrap": self.wrap,
            "repeat": self.repeat,
            "image": self.image.lower_in_object(object_data)
        }
        data.update(self.properties)
        return data


class GenericMaterial(Material):
    def __init__(self, properties):
        self.properties = properties
        self.uuid = str(uuid.uuid1())

    def lower(self, object_data):
        data = {"uuid": self.uuid}
        data.update(self.properties)
        if "map" in data:
            texture = data["map"]
            data["map"] = texture.lower_in_object(object_data)
        return data


class Object(SceneElement):
    def __init__(self, geometry, material=MeshPhongMaterial()):
        super(Object, self).__init__()
        self.geometry = geometry
        self.material = material

    def lower(self):
        data = {
            "metadata": {
                "version": 4.5,
                "type": "Object",
            },
            "geometries": [],
            "materials": [],
            "object": {
                "uuid": self.uuid,
                "type": self._type,
                "geometry": self.geometry.uuid,
                "material": self.material.uuid,
                "matrix": list(self.geometry.intrinsic_transform().flatten())
            }
        }
        self.geometry.lower_in_object(data)
        self.material.lower_in_object(data)
        return data


class Mesh(Object):
    _type = "Mesh"


def item_size(array):
    if array.ndim == 1:
        return 1
    elif array.ndim == 2:
        return array.shape[0]
    else:
        raise ValueError("I can only pack 1- or 2-dimensional numpy arrays, but this one has {:d} dimensions".format(array.ndim))


def threejs_type(dtype):
    if dtype == np.uint8:
        return "Uint8Array", 0x12
    elif dtype == np.int32:
        return "Int32Array", 0x15
    elif dtype == np.uint32:
        return "Uint32Array", 0x16
    elif dtype == np.float32:
        return "Float32Array", 0x17
    else:
        raise ValueError("Unsupported datatype: " + str(dtype))


def pack_numpy_array(x):
    if x.dtype == np.float64:
        x = x.astype(np.float32)
    typename, extcode = threejs_type(x.dtype)
    return {
        "itemSize": item_size(x),
        "type": typename,
        "array": umsgpack.Ext(extcode, x.tobytes()),
        "normalized": False
    }


class ObjMeshGeometry(Geometry):
    def __init__(self, contents):
        super(ObjMeshGeometry, self).__init__()
        self.contents = contents

    def lower(self, object_data):
        return {
            "type": "_meshfile",
            "uuid": self.uuid,
            "format": "obj",
            "data": self.contents
        }

    @staticmethod
    def from_file(fname):
        with open(fname, "r") as f:
            return ObjMeshGeometry(f.read())


class PointsGeometry(Geometry):
    def __init__(self, position, color=None):
        super(PointsGeometry, self).__init__()
        self.position = position
        self.color = color

    def lower(self, object_data):
        attrs = {"position": pack_numpy_array(self.position)}
        if self.color is not None:
            attrs["color"] = pack_numpy_array(self.color)
        return {
            "uuid": self.uuid,
            "type": "BufferGeometry",
            "data": {
                "attributes": attrs
            }
        }


class PointsMaterial(Material):
    def __init__(self, size=0.001, color=0xffffff):
        super(PointsMaterial, self).__init__()
        self.size = size
        self.color = color

    def lower(self, object_data):
        return {
            "uuid": self.uuid,
            "type": "PointsMaterial",
            "color": self.color,
            "size": self.size,
            "vertexColors": 2
        }


class Points(Object):
    _type = "Points"


def PointCloud(position, color, **kwargs):
    return Points(
        PointsGeometry(position, color),
        PointsMaterial(**kwargs)
    )



