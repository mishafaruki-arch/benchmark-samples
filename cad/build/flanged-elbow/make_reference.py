# Builds the reference FCStd for the flanged-elbow task.
import math
import os

import FreeCAD as App, Part

V = App.Vector
doc = App.newDocument("FlangedElbow")
body = doc.addObject("PartDesign::Body", "Body")
xy, yz = doc.getObject("XY_Plane"), doc.getObject("YZ_Plane")
RO, RI, RB = 20.0, 16.0, 60.0          # pipe outer/inner radius, bend radius
FT, FW, FR = 12.0, 80.0, 8.0           # flange thickness, width, corner radius
HOLE_R, HOLE_OFF = 4.5, 30.0


def sketch(name, support, offset=0.0):
    s = body.newObject("Sketcher::SketchObject", name)
    s.AttachmentSupport = [(support, "")]
    s.MapMode = "FlatFace"
    s.AttachmentOffset = App.Placement(V(0, 0, offset), App.Rotation())
    return s


def circle(s, cx, cy, r):
    s.addGeometry(Part.Circle(V(cx, cy, 0), V(0, 0, 1), r))


def rounded_square(s, cx, cy, w, r):
    h = w / 2
    c = [(cx + h - r, cy + h - r), (cx - h + r, cy + h - r), (cx - h + r, cy - h + r), (cx + h - r, cy - h + r)]
    for i, (ox, oy) in enumerate(c):
        a0 = math.radians(90 * i)
        s.addGeometry(Part.ArcOfCircle(Part.Circle(V(ox, oy, 0), V(0, 0, 1), r), a0, a0 + math.pi / 2))
    s.addGeometry(Part.LineSegment(V(cx + h - r, cy + h, 0), V(cx - h + r, cy + h, 0)))
    s.addGeometry(Part.LineSegment(V(cx - h, cy + h - r, 0), V(cx - h, cy - h + r, 0)))
    s.addGeometry(Part.LineSegment(V(cx - h + r, cy - h, 0), V(cx + h - r, cy - h, 0)))
    s.addGeometry(Part.LineSegment(V(cx + h, cy - h + r, 0), V(cx + h, cy + h - r, 0)))


# Inlet flange (z = 0..12) and straight inlet pipe (z = 12..40)
f1 = sketch("InletFlangeSketch", xy)
rounded_square(f1, 0, 0, FW, FR); circle(f1, 0, 0, RI)
p = body.newObject("PartDesign::Pad", "InletFlange"); p.Profile = f1; p.Length = FT; doc.recompute()
s1 = sketch("InletPipeSketch", xy, FT)
circle(s1, 0, 0, RO); circle(s1, 0, 0, RI)
p = body.newObject("PartDesign::Pad", "InletPipe"); p.Profile = s1; p.Length = 40 - FT; doc.recompute()

# 90 degree bend: revolve the pipe annulus at z = 40 about a Y-parallel axis through (60, 0, 40)
axis = body.newObject("PartDesign::Line", "BendAxis")
axis.MapMode = "Deactivated"
axis.Placement = App.Placement(V(RB, 0, 40), App.Rotation(V(0, 0, 1), V(0, 1, 0)))
doc.recompute()
s2 = sketch("BendSketch", xy, 40)
circle(s2, 0, 0, RO); circle(s2, 0, 0, RI)
bend = body.newObject("PartDesign::Revolution", "Bend")
bend.Profile = s2
bend.ReferenceAxis = (axis, [""])
bend.Angle = 90
doc.recompute()
if bend.Shape.BoundBox.ZMax < 99:          # revolve went the wrong way: flip it
    bend.Reversed = True
    doc.recompute()

# Straight outlet pipe (x = 60..88) and outlet flange (x = 88..100), axis along X at z = 100
s3 = sketch("OutletPipeSketch", yz, RB)
circle(s3, 0, 100, RO); circle(s3, 0, 100, RI)
p = body.newObject("PartDesign::Pad", "OutletPipe"); p.Profile = s3; p.Length = 28; doc.recompute()
f2 = sketch("OutletFlangeSketch", yz, 88)
rounded_square(f2, 0, 100, FW, FR); circle(f2, 0, 100, RI)
p = body.newObject("PartDesign::Pad", "OutletFlange"); p.Profile = f2; p.Length = FT; doc.recompute()

# Bolt holes: 4 per flange on a 60 mm square, through the flange thickness
h1 = sketch("InletBoltHoleSketch", xy)
for sx in (-1, 1):
    for sy in (-1, 1):
        circle(h1, sx * HOLE_OFF, sy * HOLE_OFF, HOLE_R)
p = body.newObject("PartDesign::Pocket", "InletBoltHoles"); p.Profile = h1; p.Length = FT; p.Reversed = True; doc.recompute()
h2 = sketch("OutletBoltHoleSketch", yz, 100)
for sy in (-1, 1):
    for sz in (-1, 1):
        circle(h2, sy * HOLE_OFF, 100 + sz * HOLE_OFF, HOLE_R)
p = body.newObject("PartDesign::Pocket", "OutletBoltHoles"); p.Profile = h2; p.Length = FT; doc.recompute()
body.Tip = p
doc.recompute()

s = body.Shape
bb = s.BoundBox
for o in body.Group:
    if o.TypeId.startswith("PartDesign::") and getattr(o, "Shape", None) and o.Shape.Solids:
        print("STEP %-18s vol=%.3f" % (o.Name, o.Shape.Volume))
print("SOLIDS", len(s.Solids), "VALID", s.isValid())
print("VOLUME %.4f AREA %.4f" % (s.Volume, s.Area))
print("BBOX x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]" % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
doc.saveAs(os.environ.get("OUT", "/out/reference.FCStd"))
