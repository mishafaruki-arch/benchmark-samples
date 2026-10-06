# Independent check of the flanged-elbow reference: classifies random points with a
# plain-math description of the part (no FreeCAD geometry) and compares them
# with FreeCAD's solid. Every point should agree.
#
#   REF=/ref/reference.FCStd freecadcmd implicit_check.py
import math, os, random
import FreeCAD as App

def rsq(u, v, h=40.0, r=8.0):                   # inside an 80x80 square with R8 corners centered at 0
    du, dv = abs(u) - (h - r), abs(v) - (h - r)
    if abs(u) > h or abs(v) > h: return False
    if du > 0 and dv > 0: return math.hypot(du, dv) <= r
    return True

def inside(x, y, z):
    # inlet flange
    if 0 <= z <= 12 and rsq(x, y) and math.hypot(x, y) >= 16:
        if not any(math.hypot(x - sx * 30, y - sy * 30) < 4.5 for sx in (-1, 1) for sy in (-1, 1)):
            return True
    # inlet pipe
    if 12 <= z <= 40 and 16 <= math.hypot(x, y) <= 20: return True
    # bend: angle about the axis through (60, *, 40) parallel to Y
    u, w = 60 - x, z - 40
    if u >= 0 and w >= 0:
        d = math.hypot(math.hypot(u, w) - 60, y)
        if 16 <= d <= 20: return True
    # outlet pipe
    if 60 <= x <= 88 and 16 <= math.hypot(y, z - 100) <= 20: return True
    # outlet flange
    if 88 <= x <= 100 and rsq(y, z - 100) and math.hypot(y, z - 100) >= 16:
        if not any(math.hypot(y - sy * 30, z - 100 - sz * 30) < 4.5 for sy in (-1, 1) for sz in (-1, 1)):
            return True
    return False

d = App.openDocument(os.environ.get("REF", "/ref/reference.FCStd"))
s = [o for o in d.Objects if o.TypeId == "PartDesign::Body"][0].Shape
random.seed(11); n = 20000; agree = ins = 0; bad = []
for _ in range(n):
    p = (random.uniform(-40, 100), random.uniform(-40, 40), random.uniform(0, 140))
    a = inside(*p); b = s.isInside(App.Vector(*p), 1e-7, True)
    agree += (a == b); ins += a
    if a != b: bad.append(p)
print("IMPLICIT agree %d/%d (%.3f%%), points inside %d" % (agree, n, 100 * agree / n, ins))
for p in bad[:5]: print("  mismatch at (%.3f, %.3f, %.3f)" % p)
