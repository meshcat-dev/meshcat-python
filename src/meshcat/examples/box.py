import math
import time

import meshcat

vis = meshcat.Visualizer().open()
box = meshcat.geometry.Box([0.5, 0.5, 0.5])
vis.set_object(box)

for i in range(200):
    theta = (i + 1) / 100 * 2 * math.pi
    vis.set_transform(meshcat.transformations.rotation_matrix(theta, [0, 0, 1]))
    time.sleep(0.01)

vis.close()
