from __future__ import absolute_import, division, print_function

import sys
if sys.version_info >= (3, 0):
    unicode = str

import bisect
from . import transformations as tf


class AnimationTrack(object):
    __slots__ = ["name", "jstype", "frames", "values"]

    def __init__(self, name, jstype, frames=None, values=None):
        self.name = name
        self.jstype = jstype
        if frames is None:
            self.frames = []
        else:
            self.frames = frames
        if values is None:
            self.values = []
        else:
            self.values = values

    def set_property(self, frame, value):
        i = bisect.bisect(self.frames, frame)
        self.frames.insert(i, frame)
        self.values.insert(i, value)

    def lower(self):
        return {
            u"name": unicode("." + self.name),
            u"type": self.jstype,
            u"keys": [{
                u"time": self.frames[i],
                u"value": self.values[i]
            } for i in range(len(self.frames))]
        }


class AnimationClip(object):
    __slots__ = ["tracks", "fps", "name"]

    def __init__(self, tracks=None, fps=30, name="default"):
        if tracks is None:
            self.tracks = {}
        else:
            self.tracks = tracks
        self.fps = fps
        self.name = name

    def set_property(self, frame, property, jstype, value):
        if property not in self.tracks:
            self.tracks[property] = AnimationTrack(property, jstype)
        track = self.tracks[property]
        track.set_property(frame, value)

    def lower(self):
        return {
            u"fps": self.fps,
            u"name": self.name,
            u"tracks": [t.lower() for t in self.tracks.values()]
        }


class Animation(object):
    __slots__ = ["clips", "default_framerate"]

    def __init__(self, clips=None, default_framerate=30):
        if clips is None:
            self.clips = {}
        else:
            self.clips = clips
        self.default_framerate = default_framerate

    def lower(self):
        return [{
            u"path": path.lower(),
            u"clip": clip.lower()
        } for (path, clip) in self.clips.items()]

    def at_frame(self, visualizer, frame):
        return AnimationFrameVisualizer(self, visualizer.path, frame)


def js_position(matrix):
    return list(matrix[:3, 3])


def js_quaternion(matrix):
    quat = tf.quaternion_from_matrix(matrix)
    return [quat[1], quat[2], quat[3], quat[0]]


class AnimationFrameVisualizer(object):
    __slots__ = ["animation", "path", "current_frame"]

    def __init__(self, animation, path, current_frame):
        self.animation = animation
        self.path = path
        self.current_frame = current_frame

    def get_clip(self):
        if self.path not in self.animation.clips:
            self.animation.clips[self.path] = AnimationClip(fps=self.animation.default_framerate)
        return self.animation.clips[self.path]

    def set_transform(self, matrix):
        clip = self.get_clip()
        clip.set_property(self.current_frame, "position", "vector3", js_position(matrix))
        clip.set_property(self.current_frame, "quaternion", "quaternion", js_quaternion(matrix))

    def set_property(self, prop, jstype, value):
        clip = self.get_clip()
        clip.set_property(self.current_frame, prop, jstype, value)

    def __getitem__(self, path):
        return AnimationFrameVisualizer(self.animation, self.path.append(path), self.current_frame)

    def __enter__(self):
        return self

    def __exit__(self, *arg):
        pass
