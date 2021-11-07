import base64
import uuid
from io import StringIO, BytesIO
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


class GenericMaterial(Material):
    def __init__(self, color=0xffffff, reflectivity=0.5, map=None,
                 side = 2, transparent = None, opacity = 1.0,
                 linewidth = 1.0,
                 wireframe = False,
                 wireframeLinewidth = 1.0,
                 vertexColors=False,
                 **kwargs):
        super(GenericMaterial, self).__init__()
        self.color = color
        self.reflectivity = reflectivity
        self.map = map
        self.side = side
        self.transparent = transparent
        self.opacity = opacity
        self.linewidth = linewidth
        self.wireframe = wireframe
        self.wireframeLinewidth = wireframeLinewidth
        self.vertexColors = vertexColors
        self.properties = kwargs

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
            u"opacity": self.opacity,
            u"linewidth": self.linewidth,
            u"wireframe": bool(self.wireframe),
            u"wireframeLinewidth": self.wireframeLinewidth,
            u"vertexColors": (2 if self.vertexColors else 0),  # three.js wants an enum
        }
        data.update(self.properties)
        if self.map is not None:
            data[u"map"] = self.map.lower_in_object(object_data)
        return data


class MeshBasicMaterial(GenericMaterial):
    _type=u"MeshBasicMaterial"


class MeshPhongMaterial(GenericMaterial):
    _type=u"MeshPhongMaterial"


class MeshLambertMaterial(GenericMaterial):
    _type=u"MeshLambertMaterial"


class MeshToonMaterial(GenericMaterial):
    _type=u"MeshToonMaterial"


class LineBasicMaterial(GenericMaterial):
    _type=u"LineBasicMaterial"


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
            u"url": str("data:image/png;base64," + base64.b64encode(self.data).decode('ascii'))
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


class OrthographicCamera(SceneElement):
    def __init__(self, left, right, top, bottom, near, far, zoom=1):
        super(OrthographicCamera, self).__init__()
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.near = near
        self.far = far
        self.zoom = zoom

    def lower(self):
        data = {
            u"object": {
                u"uuid": self.uuid,
                u"type": u"OrthographicCamera",
                u"left": self.left,
                u"right": self.right,
                u"top": self.top,
                u"bottom": self.bottom,
                u"near": self.near,
                u"far": self.far,
                u"zoom": self.zoom,
            }
        }
        return data

class PerspectiveCamera(SceneElement):
    """
    The PerspectiveCamera is the default camera used by the meshcat viewer. See
    https://threejs.org/docs/#api/en/cameras/PerspectiveCamera for more
    information.
    """
    def __init__(self, fov = 50, aspect = 1, near = 0.1, far = 2000,
                 zoom = 1, filmGauge=35, filmOffset = 0, focus = 10):
        """
        fov   : Camera frustum vertical field of view, from bottom to top of view, in degrees. Default is 50.
        aspect: Camera frustum aspect ratio, usually the canvas width / canvas height. Default is 1 (square canvas).
        near  : Camera frustum near plane. Default is 0.1. The valid range is greater than 0 and less than the current
                value of the far plane. Note that, unlike for the OrthographicCamera, 0 is not a valid value for a
                PerspectiveCamera's near plane.
        far   : Camera frustum far plane. Default is 2000.
        zoom  : Gets or sets the zoom factor of the camera. Default is 1.
        filmGauge: Film size used for the larger axis. Default is 35 (millimeters). This parameter does not influence
                   the projection matrix unless .filmOffset is set to a nonzero value.
        filmOffset: Horizontal off-center offset in the same unit as .filmGauge. Default is 0.
        focus: Object distance used for stereoscopy and depth-of-field effects. This parameter does not influence
               the projection matrix unless a StereoCamera is being used. Default is 10.
        """
        #super(PerspectiveCamera, self).__init__()
        SceneElement.__init__(self)
        self.fov = fov
        self.aspect = aspect
        self.far = far
        self.near = near
        self.zoom = zoom
        self.filmGauge = filmGauge
        self.filmOffset = filmOffset
        self.focus = focus

    def lower(self):
        data = {
            u"object": {
                u"uuid": self.uuid,
                u"type": u"PerspectiveCamera",
                u"aspect": self.aspect,
                u"far": self.far,
                u"filmGauge": self.filmGauge,
                u"filmOffset": self.filmOffset,
                u"focus": self.focus,
                u"fov": self.fov,
                u"near": self.near,
                u"zoom": self.zoom,
            }
        }
        return data

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
    if isinstance(stream, BytesIO):
        data = stream.read().decode(encoding='utf-8')
    elif isinstance(stream, StringIO):
        data = stream.read()
    else:
        raise ValueError('Stream must be instance of StringIO or BytesIO, not {}'.format(type(stream)))
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
        if isinstance(f, BytesIO):
            arr  = np.frombuffer(f.read(), dtype=np.uint8)
        elif isinstance(f, StringIO):
            arr = np.frombuffer(bytes(f.read(), "utf-8"), dtype=np.uint8)
        else:
            raise ValueError('Stream must be instance of StringIO or BytesIO, not {}'.format(type(f)))
        _, extcode = threejs_type(np.uint8)
        encoded = umsgpack.Ext(extcode, arr.tobytes())
        return MeshGeometry(encoded, u"stl")


class TriangularMeshGeometry(Geometry):
    """
    A mesh consisting of an arbitrary collection of triangular faces. To
    construct one, you need to pass in a collection of vertices as an Nx3 array
    and a collection of faces as an Mx3 array. Each element of `faces` should
    be a collection of 3 indices into the `vertices` array.

    For example, to create a square made out of two adjacent triangles, we
    could do:

    vertices = np.array([
        [0, 0, 0],  # the first vertex is at [0, 0, 0]
        [1, 0, 0],
        [1, 0, 1],
        [0, 0, 1]
    ])
    faces = np.array([
        [0, 1, 2],  # The first face consists of vertices 0, 1, and 2
        [3, 0, 2]
    ])

    mesh = TriangularMeshGeometry(vertices, faces)

    To set the color of the mesh by vertex, pass an Nx3 array containing the
    RGB values (in range [0,1]) of the vertices to the optional `color`
    argument, and set `vertexColors=True` in the Material.
    """
    __slots__ = ["vertices", "faces"]

    def __init__(self, vertices, faces, color=None):
        super(TriangularMeshGeometry, self).__init__()

        vertices = np.asarray(vertices, dtype=np.float32)
        faces = np.asarray(faces, dtype=np.uint32)
        assert vertices.shape[1] == 3, "`vertices` must be an Nx3 array"
        assert faces.shape[1] == 3, "`faces` must be an Mx3 array"
        self.vertices = vertices
        self.faces = faces
        if color is not None:
            color = np.asarray(color, dtype=np.float32)
            assert np.array_equal(vertices.shape, color.shape), "`color` must be the same shape as vertices"
        self.color = color

    def lower(self, object_data):
        attrs = {u"position": pack_numpy_array(self.vertices.T)}
        if self.color is not None:
            attrs[u"color"] = pack_numpy_array(self.color.T)
        return {
            u"uuid": self.uuid,
            u"type": u"BufferGeometry",
            u"data": {
                u"attributes": attrs,
                u"index": pack_numpy_array(self.faces.T)
            }
        }


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


def triad(scale=1.0):
    """
    A visual representation of the origin of a coordinate system, drawn as three
    lines in red, green, and blue along the x, y, and z axes. The `scale` parameter
    controls the length of the three lines.

    Returns an `Object` which can be passed to `set_object()`
    """
    return LineSegments(
        PointsGeometry(position=np.array([
            [0, 0, 0], [scale, 0, 0],
            [0, 0, 0], [0, scale, 0],
            [0, 0, 0], [0, 0, scale]]).astype(np.float32).T,
            color=np.array([
            [1, 0, 0], [1, 0.6, 0],
            [0, 1, 0], [0.6, 1, 0],
            [0, 0, 1], [0, 0.6, 1]]).astype(np.float32).T
        ),
        LineBasicMaterial(vertexColors=True))
