from __future__ import absolute_import, division, print_function

import sys
if sys.version_info >= (3, 0):
    unicode = str

from .geometry import (Geometry, Plane, Object, Mesh,
MeshPhongMaterial, PointsMaterial, Points, TextTexture)

class SetObject:
    __slots__ = ["object", "path"]

    def __init__(self, geometry_or_object, material=None, path=[]):
        if isinstance(geometry_or_object, Object):
            if material is not None:
                raise(ArgumentError(
                    "Please supply either an Object OR a Geometry and a Material"))
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


class SetText:
    __slots__ = ["object", "path"]

    def __init__(self, text, geometry_or_object, plane_width=10,
        plane_height=5, material=None, path=[], **kwargs):
        self.text_texture = TextTexture(text, **kwargs)
        if isinstance(geometry_or_object, Object):
            if material is not None:
                raise(ArgumentError(
                    "Please supply either an Object OR a Geometry and a Material"))
            self.object = geometry_or_object
        else:
            if geometry_or_object is None:
                geometry_or_object = Plane(width=plane_width, height=plane_height)
                # if writing onto the scene, default material is transparent
                material = MeshPhongMaterial(map=self.text_texture,
                                             needsUpdate=True, transparent=True)
            if material is None:
                material = MeshPhongMaterial(map=self.text_texture,
                                             needsUpdate=True)
            if isinstance(material, PointsMaterial):
                raise(ArgumentError(
                    "Cannot write text onto points; please supply a mesh material"))
            else:
                self.object = Mesh(geometry_or_object, material)
        self.path = path

    def lower(self):
        data = {
            u"type": u"set_text",
            u"object": self.object.lower(),
            u"path": self.path.lower()
        }
        self.text_texture.lower_in_object(data)
        return data


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
