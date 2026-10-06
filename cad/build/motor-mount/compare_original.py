# Checks the reference against the original SolidWorks part it was rebuilt from
# (original.step, rotated into task coordinates) by classifying random points.
# The only intended difference is the 0.25 mm edge chamfers the reference omits.
#
#   REF=/ref/reference.FCStd ORIG=/build/motor-mount/original.step freecadcmd compare_original.py
import os
import random

import FreeCAD as App, Part

V = App.Vector
d = App.openDocument(os.environ.get("REF", "/ref/reference.FCStd"))
ref = [o for o in d.Objects if o.TypeId == "PartDesign::Body"][0].Shape.Solids[0]
orig = Part.read(os.environ.get("ORIG", "/build/motor-mount/original.step"))
orig.rotate(V(0, 0, 0), V(1, 0, 0), 90)       # (x, y, z) -> (x, -z, y): plate into the XY plane
orig = orig.Solids[0]
print("VOLUME reference=%.4f original=%.4f (%.3f%%)" % (ref.Volume, orig.Volume, 100 * (ref.Volume - orig.Volume) / orig.Volume))
random.seed(1)
bb, n, agree = ref.BoundBox, 20000, 0
for _ in range(n):
    p = V(random.uniform(bb.XMin, bb.XMax), random.uniform(bb.YMin, bb.YMax), random.uniform(bb.ZMin, bb.ZMax))
    agree += ref.isInside(p, 1e-6, True) == orig.isInside(p, 1e-6, True)
print("POINTS agree %d/%d" % (agree, n))
