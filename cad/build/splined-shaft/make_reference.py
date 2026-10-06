# Builds the reference FCStd for the splined-shaft task.
import math
import os

import FreeCAD as App, Part

V = App.Vector
doc = App.newDocument("SplinedShaft")
body = doc.addObject("PartDesign::Body", "Body")
xy, xz, yz = (doc.getObject(n) for n in ("XY_Plane", "XZ_Plane", "YZ_Plane"))


def sketch(name, support, offset=0.0):
    s = body.newObject("Sketcher::SketchObject", name)
    s.AttachmentSupport = [(support, "")]
    s.MapMode = "FlatFace"
    s.AttachmentOffset = App.Placement(V(0, 0, offset), App.Rotation())
    return s


def polyline(s, pts):
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))


# --- Stepped body: revolve the half-profile (radius, z) about the Z axis --------
prof = sketch("ShaftProfile", xz)
polyline(prof, [(0, 0), (11.5, 0), (12.5, 1), (12.5, 40), (15, 40), (15, 90), (20, 90), (20, 100),
                (15, 100), (15, 140), (10, 140), (10, 174), (9, 175), (0, 175)])
rev = body.newObject("PartDesign::Revolution", "ShaftRevolution")
rev.Profile = prof
rev.ReferenceAxis = (prof, ["V_Axis"])
rev.Angle = 360
doc.recompute()

# --- Retaining-ring groove: 2 mm wide, down to diameter 28, at z = 82..84 -------
gp = sketch("GrooveProfile", xz)
polyline(gp, [(14, 82), (16, 82), (16, 84), (14, 84)])
groove = body.newObject("PartDesign::Groove", "RetainingRingGroove")
groove.Profile = gp
groove.ReferenceAxis = (gp, ["V_Axis"])
groove.Angle = 360
doc.recompute()

# --- Spline: 6 straight-sided teeth (width 6) on the 25 mm end, minor diameter 21,
#     30 mm long from z = 0. Each space between teeth is cut in one sketch. ------
sp = sketch("SplineSpacesSketch", xy)
R_MIN, R_OUT, HALF = 10.5, 14.0, 3.0
for k in range(6):
    phi = math.radians(60 * k)          # tooth k is centered on this angle
    a_in0 = phi + math.asin(HALF / R_MIN); a_in1 = phi + math.radians(60) - math.asin(HALF / R_MIN)
    a_out0 = phi + math.asin(HALF / R_OUT); a_out1 = phi + math.radians(60) - math.asin(HALF / R_OUT)
    p = lambda r, a: V(r * math.cos(a), r * math.sin(a), 0)
    sp.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), R_MIN), a_in0, a_in1))
    sp.addGeometry(Part.LineSegment(p(R_MIN, a_in1), p(R_OUT, a_out1)))
    sp.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), R_OUT), a_out0, a_out1))
    sp.addGeometry(Part.LineSegment(p(R_OUT, a_out0), p(R_MIN, a_in0)))
spl = body.newObject("PartDesign::Pocket", "SplineSpaces")
spl.Profile = sp
spl.Length = 30
spl.Reversed = True
doc.recompute()

# --- Keyway: 6 mm wide slot with round ends, z = 145..170, on +X, floor at x = 6.5
ks = sketch("KeywaySketch", yz, 10.0)
ks.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 148, 0), V(0, 0, 1), 3), math.pi, 2 * math.pi))
ks.addGeometry(Part.LineSegment(V(3, 148, 0), V(3, 167, 0)))
ks.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 167, 0), V(0, 0, 1), 3), 0, math.pi))
ks.addGeometry(Part.LineSegment(V(-3, 167, 0), V(-3, 148, 0)))
key = body.newObject("PartDesign::Pocket", "Keyway")
key.Profile = ks
key.Length = 3.5
doc.recompute()

# --- Cross hole: diameter 5 through the shaft along Y at z = 120 -----------------
hs = sketch("CrossHoleSketch", xz)
hs.addGeometry(Part.Circle(V(0, 120, 0), V(0, 0, 1), 2.5))
hole = body.newObject("PartDesign::Pocket", "CrossHole")
hole.Profile = hs
hole.Length = 50
hole.Midplane = True
doc.recompute()
body.Tip = hole
doc.recompute()

s = body.Shape
bb = s.BoundBox
for o in body.Group:
    if o.TypeId.startswith("PartDesign::") and getattr(o, "Shape", None) and o.Shape.Solids:
        print("STEP %-20s vol=%.3f" % (o.Name, o.Shape.Volume))
print("SOLIDS", len(s.Solids), "VALID", s.isValid())
print("VOLUME %.4f AREA %.4f" % (s.Volume, s.Area))
print("BBOX x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]" % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
doc.saveAs(os.environ.get("OUT", "/out/reference.FCStd"))
