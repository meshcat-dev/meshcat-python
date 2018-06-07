from __future__ import absolute_import, division, print_function

import sys
if sys.version_info >= (3, 0):
    unicode = str

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
            u"type": u"set_object",
            u"object": self.object.lower(),
            u"path": self.path.lower()
        }


class SetTransform:
    __slots__ = ["matrix", "path"]
    def __init__(self, matrix, path=[]):
        self.matrix = matrix
        self.path = path

    def lower(self):
        return {
            u"type": u"set_transform",
            u"path": self.path.lower(),
            u"matrix": list(self.matrix.T.flatten())
        }


class Delete:
    __slots__ = ["path"]
    def __init__(self, path):
        self.path = path

    def lower(self):
        return {
            u"type": u"delete",
            u"path": self.path.lower()
        }


class SetAnimation:
    __slots__ = ["animation", "play", "repetitions"]

    def __init__(self, animation, play=True, repetitions=1):
        self.animation = animation
        self.play = play
        self.repetitions = repetitions

    def lower(self):
        return {
            u"type": u"set_animation",
            u"animations": self.animation.lower(),
            u"options": {
                u"play": self.play,
                u"repetitions": self.repetitions
            },
            u"path": ""
        }
