# Builds the reference FCStd for the impeller task.
import math
import os

import FreeCAD as App, Part

V = App.Vector
doc = App.newDocument("Impeller")
body = doc.addObject("PartDesign::Body", "Body")
xy, xz = doc.getObject("XY_Plane"), doc.getObject("XZ_Plane")
N_BLADES = 7
C = (0.0, 50.0)                         # blade arc center for the blade starting on +X
R_IN, R_OUT = 48.5, 51.5                # blade faces (blade thickness 3)
RHUB_CUT, RTIP = 12.0, 58.0             # blade profile runs from inside the hub to the tip circle


def sketch(name, support, offset=0.0):
    s = body.newObject("Sketcher::SketchObject", name)
    s.AttachmentSupport = [(support, "")]
    s.MapMode = "FlatFace"
    s.AttachmentOffset = App.Placement(V(0, 0, offset), App.Rotation())
    return s


def rot(p, a):
    return (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a))


def meet(R, rho):
    """Point (x >= 0) where the circle |p - C| = R meets the circle |p| = rho."""
    y = (rho ** 2 + C[0] ** 2 + C[1] ** 2 - R ** 2) / (2 * C[1])
    return (math.sqrt(rho ** 2 - y ** 2), y)


def short_arc(center, r, p0, p1):
    a0 = math.atan2(p0[1] - center[1], p0[0] - center[0])
    a1 = math.atan2(p1[1] - center[1], p1[0] - center[0])
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi      # signed short sweep
    lo, hi = (a0, a0 + d) if d > 0 else (a0 + d, a0)
    return Part.ArcOfCircle(Part.Circle(V(center[0], center[1], 0), V(0, 0, 1), r), lo, hi)


# Back plate: diameter 120, 4 thick
bp = sketch("BackPlateSketch", xy)
bp.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 60))
pad = body.newObject("PartDesign::Pad", "BackPlate"); pad.Profile = bp; pad.Length = 4; doc.recompute()

# Hub: revolve (r, z) profile: cylinder r15 from z 4 to 28, cone to r8 at z 36
hp = sketch("HubProfile", xz)
pts = [(0, 4), (15, 4), (15, 28), (8, 36), (0, 36)]
for a, b in zip(pts, pts[1:] + pts[:1]):
    hp.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
hub = body.newObject("PartDesign::Revolution", "Hub"); hub.Profile = hp
hub.ReferenceAxis = (hp, ["V_Axis"]); hub.Angle = 360; doc.recompute()

# Blades: 7 backward-curved blades, 20 high (z 4..24), all in one sketch
bs = sketch("BladeSketch", xy, 4)
for k in range(N_BLADES):
    a = 2 * math.pi * k / N_BLADES
    c = rot(C, a)
    A1, B1 = rot(meet(R_IN, RHUB_CUT), a), rot(meet(R_IN, RTIP), a)
    A2, B2 = rot(meet(R_OUT, RHUB_CUT), a), rot(meet(R_OUT, RTIP), a)
    bs.addGeometry(short_arc(c, R_IN, A1, B1))
    bs.addGeometry(short_arc((0, 0), RTIP, B1, B2))
    bs.addGeometry(short_arc(c, R_OUT, B2, A2))
    bs.addGeometry(short_arc((0, 0), RHUB_CUT, A2, A1))
blades = body.newObject("PartDesign::Pad", "Blades"); blades.Profile = bs; blades.Length = 20; doc.recompute()

# D-shaped bore: diameter 10 with a flat at x = 4, through the part
ds = sketch("DBoreSketch", xy, 36)
t = math.acos(4 / 5)
ds.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), 5), t, 2 * math.pi - t))
ds.addGeometry(Part.LineSegment(V(4, -3, 0), V(4, 3, 0)))
bore = body.newObject("PartDesign::Pocket", "DBore"); bore.Profile = ds; bore.Type = 1; doc.recompute()
body.Tip = bore
doc.recompute()

s = body.Shape
bb = s.BoundBox
for o in body.Group:
    if o.TypeId.startswith("PartDesign::") and getattr(o, "Shape", None) and o.Shape.Solids:
        print("STEP %-12s vol=%.3f" % (o.Name, o.Shape.Volume))
print("SOLIDS", len(s.Solids), "VALID", s.isValid())
print("VOLUME %.4f AREA %.4f" % (s.Volume, s.Area))
print("BBOX x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]" % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
doc.saveAs(os.environ.get("OUT", "/out/reference.FCStd"))
