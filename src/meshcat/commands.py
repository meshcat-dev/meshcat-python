from __future__ import absolute_import, division, print_function

from .geometry import Geometry, Object, Mesh, MeshPhongMaterial, PointsMaterial, Points

class SetObject:
    __slots__ = ["object", "path"]
    def __init__(self, geometry_or_object, material=None, path=[]):
        if isinstance(geometry_or_object, Object):
            if material is not None:
                raise(ArgumentError("Please supply either an Object OR a Geometry and a Material"))
            self.object = geometry_or_object
        else:
            if material is None:
                material = MeshPhongMaterial()
            if isinstance(material, PointsMaterial):
                self.object = Points(geometry_or_object, material)
            else:
                self.object = Mesh(geometry_or_object, material)
        self.path = path

    def lower(self):
        return {
            "type": "set_object",
            "object": self.object.lower(),
            "path": self.path
        }


class SetTransform:
    __slots__ = ["matrix", "path"]
    def __init__(self, matrix, path=[]):
        self.matrix = matrix
        self.path = path

    def lower(self):
        return {
            "type": "set_transform",
            "path": self.path,
            "matrix": list(self.matrix.T.flatten())
        }


class Delete:
    __slots__ = ["path"]
    def __init__(self, path):
        self.path = path

    def lower(self):
        return {
            "type": "delete",
            "path": self.path
        }
