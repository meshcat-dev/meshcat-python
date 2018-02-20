from .geometry import Geometry, Mesh

class SetObject:
    __slots__ = ["object", "path"]
    def __init__(self, object, path=[]):
        if isinstance(object, Geometry):
            self.object = Mesh(object)
        else:
            self.object = object
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


class ViewerMessage:
    def __init__(self, commands):
        self.commands = commands

    def lower(self):
        return {
            "commands": [c.lower() for c in self.commands]
        }
