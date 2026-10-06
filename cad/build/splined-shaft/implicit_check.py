# Independent check of the splined-shaft reference: classifies random points with a
# plain-math description of the part (no FreeCAD geometry) and compares them
# with FreeCAD's solid. Every point should agree.
#
#   REF=/ref/reference.FCStd freecadcmd implicit_check.py
import math, os, random
import FreeCAD as App

def inside(x, y, z):
    r = math.hypot(x, y)
    # stepped body with end chamfers
    if z < 0 or z > 175: return False
    if z < 1: R = 11.5 + z
    elif z < 40: R = 12.5
    elif z < 90: R = 15
    elif z < 100: R = 20
    elif z < 140: R = 15
    elif z < 174: R = 10
    else: R = 10 - (z - 174)
    if r > R: return False
    if 82 < z < 84 and r > 14: return False                       # groove
    if z < 30 and r > 10.5:                                       # spline: only teeth remain
        a = math.atan2(y, x)
        k = round(a / (math.pi / 3))
        phi = k * math.pi / 3
        perp = -x * math.sin(phi) + y * math.cos(phi)
        if abs(perp) > 3: return False
    if 145 < z < 170 and x > 6.5:                                 # keyway slot
        zc = min(max(z, 148), 167)
        if math.hypot(y, z - zc) < 3: return False
    if math.hypot(x, z - 120) < 2.5: return False                 # cross hole
    return True

d = App.openDocument(os.environ.get("REF", "/ref/reference.FCStd"))
s = [o for o in d.Objects if o.TypeId == "PartDesign::Body"][0].Shape
random.seed(7); n = 20000; agree = inside_count = 0
bad = []
for _ in range(n):
    # bias half of the samples to the spline / keyway / groove regions
    if random.random() < 0.5:
        p = (random.uniform(-20, 20), random.uniform(-20, 20), random.uniform(0, 175))
    else:
        zone = random.choice([(0, 31), (80, 86), (144, 171), (116, 124)])
        p = (random.uniform(-16, 16), random.uniform(-16, 16), random.uniform(*zone))
    a = inside(*p); b = s.isInside(App.Vector(*p), 1e-7, True)
    agree += (a == b); inside_count += a
    if a != b: bad.append(p)
print("IMPLICIT agree %d/%d (%.3f%%), points inside %d" % (agree, n, 100 * agree / n, inside_count))
for p in bad[:5]: print("  mismatch at (%.3f, %.3f, %.3f)" % p)
