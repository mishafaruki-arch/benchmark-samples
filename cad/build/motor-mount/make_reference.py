# Rebuilds the laser-cutter X-Axis Motor Mount as a PartDesign reference (sharp edges, no 0.25 mm edge breaks).
# Task coordinates: plate in the XY plane, thickness along +Z (front face at Z = 0, back face at Z = 25).
import math
import os

import FreeCAD as App, Part
V = App.Vector
T = 25.0
R_BORE, R_F, R_EAR = 25.125, 3.5, 0.5

doc = App.newDocument("MotorMount")
body = doc.addObject("PartDesign::Body", "Body")
xy = doc.getObject("XY_Plane")

def sketch(name, support, z=0.0):
    s = body.newObject("Sketcher::SketchObject", name)
    s.AttachmentSupport = [(support, "")]
    s.MapMode = "FlatFace"
    s.AttachmentOffset = App.Placement(V(0, 0, z), App.Rotation())
    return s

def arc(c, r, p0, p1):
    """Arc from p0 to p1 (counter-clockwise) around center c."""
    a0 = math.atan2(p0[1] - c[1], p0[0] - c[0]); a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
    while a1 <= a0: a1 += 2 * math.pi
    return Part.ArcOfCircle(Part.Circle(V(c[0], c[1], 0), V(0, 0, 1), r), a0, a1)

# ---- Outline: exact profile sliced from the original SolidWorks part at mid-thickness ----
src = Part.read(os.environ.get("ORIG", "/build/motor-mount/original.step"))
src.rotate(V(0, 0, 0), V(1, 0, 0), 90)       # (x, y, z) -> (x, -z, y): plate into the XY plane
wire = src.slice(V(0, 0, 1), T / 2)[0]
outline = sketch("OutlineSketch", xy)
for e in wire.Edges:
    a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
    a, b = V(a.x, a.y, 0), V(b.x, b.y, 0)
    if isinstance(e.Curve, Part.Line):
        outline.addGeometry(Part.LineSegment(a, b))
    else:
        c = e.Curve
        circ = Part.Circle(V(c.Center.x, c.Center.y, 0), V(0, 0, 1), c.Radius)
        a0 = math.atan2(a.y - c.Center.y, a.x - c.Center.x); a1 = math.atan2(b.y - c.Center.y, b.x - c.Center.x)
        mid = e.valueAt((e.FirstParameter + e.LastParameter) / 2)
        am = math.atan2(mid.y - c.Center.y, mid.x - c.Center.x)
        def ccw_between(x0, x1, xm):           # is xm on the CCW sweep from x0 to x1?
            t1 = (x1 - x0) % (2 * math.pi); tm = (xm - x0) % (2 * math.pi)
            return tm < t1
        if not ccw_between(a0, a1, am):
            a0, a1 = a1, a0
        if a1 <= a0: a1 += 2 * math.pi
        outline.addGeometry(Part.ArcOfCircle(circ, a0, a1))
pad = body.newObject("PartDesign::Pad", "PlatePad")
pad.Profile = outline
pad.Length = T
doc.recompute()

# ---- Blind holes with 118 deg drill points --------------------------------------
def holes(name, z, dia, depth, reverse):
    sk = sketch(name + "Sketch", xy, z)
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        sk.addGeometry(Part.Circle(V(35 * math.cos(a), 35 * math.sin(a), 0), V(0, 0, 1), dia / 2))
    h = body.newObject("PartDesign::Hole", name)
    h.Profile = sk
    h.Threaded = False
    h.Diameter = dia
    h.DepthType = "Dimension"
    h.Depth = depth
    h.DrillPoint = "Angled"
    h.DrillPointAngle = 118
    h.HoleCutType = "None"
    h.Reversed = reverse
    doc.recompute()
    return h
front = holes("FrontHoles", 0.0, 4.2, 12.4 - 2.1 / math.tan(math.radians(59)), True)
back = holes("BackHoles", T, 3.3, 10.1 - 1.65 / math.tan(math.radians(59)), False)

# ---- Ear holes along X ------------------------------------------------------------
yz = doc.getObject("YZ_Plane")
es = sketch("EarHoleSketch", yz)
es.AttachmentOffset = App.Placement(V(0, 0, 27), App.Rotation())
for yy in (-51.0, 51.0):
    for zz in (6.5, 18.5):
        es.addGeometry(Part.Circle(V(yy, zz, 0), V(0, 0, 1), 2.75))
ear = body.newObject("PartDesign::Pocket", "EarHoles")
ear.Profile = es
ear.Length = 12
ear.Midplane = True
doc.recompute()
body.Tip = ear
doc.recompute()

s = body.Shape
bb = s.BoundBox
print("SOLIDS", len(s.Solids), "VALID", s.isValid())
print("VOLUME %.4f AREA %.4f" % (s.Volume, s.Area))
print("BBOX x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]" % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
for o in body.Group:
    if hasattr(o, "Shape") and o.TypeId.startswith("PartDesign::") and o.Shape.Solids:
        print("STEP %-12s vol=%.3f" % (o.Name, o.Shape.Volume))
doc.saveAs(os.environ.get("OUT", "/out/reference.FCStd"))
