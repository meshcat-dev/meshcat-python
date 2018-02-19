import time
import numpy as np

import meshcat
import meshcat.geometry as g

verts = np.random.random((3, 100000)).astype(np.float32)

vis = meshcat.Visualizer().open()
vis.set_object(g.Points(
    g.PointsGeometry(verts, color=verts),
    g.PointsMaterial()
))

vis.close()
