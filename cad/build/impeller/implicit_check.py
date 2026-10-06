# Independent check of the impeller reference: classifies random points with a
# plain-math description of the part (no FreeCAD geometry) and compares them
# with FreeCAD's solid. Every point should agree.
#
#   REF=/ref/reference.FCStd freecadcmd implicit_check.py
import math, os, random
import FreeCAD as App

def inside(x, y, z):
    r = math.hypot(x, y)
    if r <= 5 and x <= 4: return False                         # D-bore (whole height)
    if 0 <= z <= 4 and r <= 60: return True                    # back plate
    if 4 <= z <= 36:                                           # hub
        R = 15 if z <= 28 else 15 - 7 * (z - 28) / 8
        if r <= R: return True
    if 4 <= z <= 24 and 12 <= r <= 58:                         # blades
        for k in range(7):
            a = -2 * math.pi * k / 7
            u, v = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
            if u >= 0 and 48.5 <= math.hypot(u, v - 50) <= 51.5:
                return True
    return False

d = App.openDocument(os.environ.get("REF", "/ref/reference.FCStd"))
s = [o for o in d.Objects if o.TypeId == "PartDesign::Body"][0].Shape
random.seed(5); n = 20000; agree = ins = 0; bad = []
for _ in range(n):
    if random.random() < 0.6:   # concentrate on the blade layer
        p = (random.uniform(-60, 60), random.uniform(-60, 60), random.uniform(4, 24))
    else:
        p = (random.uniform(-60, 60), random.uniform(-60, 60), random.uniform(0, 36))
    a = inside(*p); b = s.isInside(App.Vector(*p), 1e-7, True)
    agree += (a == b); ins += a
    if a != b: bad.append(p)
print("IMPLICIT agree %d/%d (%.3f%%), points inside %d" % (agree, n, 100 * agree / n, ins))
for p in bad[:5]: print("  mismatch at (%.3f, %.3f, %.3f)" % p)
# blade area check by fine grid integration (independent of FreeCAD)
h = 0.05; area = 0
for i in range(int(116 / h)):
    x = -58 + (i + 0.5) * h
    for j in range(int(116 / h)):
        y = -58 + (j + 0.5) * h
        r = math.hypot(x, y)
        if 15 < r <= 58 and x >= 0 and 48.5 <= math.hypot(x, y - 50) <= 51.5:
            area += h * h
print("BLADE area outside hub (one blade, grid) = %.3f mm2 -> 7 blades x 20 mm = %.2f mm3" % (area, area * 7 * 20))
