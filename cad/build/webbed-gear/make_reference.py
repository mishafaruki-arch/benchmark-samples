# Builds the reference FCStd for the webbed-gear task.
import math
import os

import FreeCAD as App, Part

V = App.Vector
M, Z, PA = 2.0, 36, math.radians(20)        # module, teeth, pressure angle
FACE, WEB = 20.0, 8.0                        # face width, web thickness
RIM_ID, HUB_D, BORE_D = 56.0, 30.0, 16.0     # rim inner diameter, hub diameter, bore
HOLES, HOLE_D, HOLE_PCD = 6, 10.0, 43.0      # lightening holes
KEY_W, KEY_TOP = 5.0, 10.3                   # keyway width, keyway floor distance from axis

rp = M * Z / 2            # pitch radius 36
ra = rp + M               # tip radius 38
rf = rp - 1.25 * M        # root radius 33.5
rb = rp * math.cos(PA)    # base radius
inv = lambda a: math.tan(a) - a
half_pitch = math.pi / (2 * Z)               # half tooth thickness angle at pitch circle
def flank_angle(r):                          # half-angle from tooth centerline at radius r
    return half_pitch + inv(PA) - inv(math.acos(rb / r))

doc = App.newDocument("WebbedGear")
body = doc.addObject("PartDesign::Body", "Body")
xy = doc.getObject("XY_Plane")

def new_sketch(name, z=0.0):
    s = body.newObject("Sketcher::SketchObject", name)
    s.AttachmentSupport = [(xy, "")]
    s.MapMode = "FlatFace"
    s.AttachmentOffset = App.Placement(V(0, 0, z), App.Rotation())
    return s

def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return V(p.x * c - p.y * s, p.x * s + p.y * c, 0)

# --- Gear outline: tooth 0 centered on +X -----------------------------------
th_tip, th_base = flank_angle(ra), flank_angle(rb)
n = 40
radii = [rb + (ra - rb) * (i / n) ** 1.5 for i in range(n + 1)]
upper = [V(r * math.cos(flank_angle(r)), r * math.sin(flank_angle(r)), 0) for r in radii]
lower = [V(p.x, -p.y, 0) for p in upper]
gear = new_sketch("GearProfile")
step = 2 * math.pi / Z
for k in range(Z):
    a = k * step
    lo_flank = Part.BSplineCurve(); lo_flank.interpolate([rot(p, a) for p in lower])
    up_flank = Part.BSplineCurve(); up_flank.interpolate([rot(p, a) for p in reversed(upper)])
    root_lo = rot(V(rf * math.cos(-th_base), rf * math.sin(-th_base), 0), a)
    base_lo = rot(lower[0], a)
    base_up = rot(upper[0], a)
    root_up = rot(V(rf * math.cos(th_base), rf * math.sin(th_base), 0), a)
    gear.addGeometry(Part.LineSegment(root_lo, base_lo))                                  # radial below base
    gear.addGeometry(lo_flank)                                                             # involute flank
    gear.addGeometry(Part.ArcOfCircle(Part.Circle(V(0,0,0), V(0,0,1), ra), a - th_tip, a + th_tip))  # tip
    gear.addGeometry(up_flank)
    gear.addGeometry(Part.LineSegment(base_up, root_up))
    gear.addGeometry(Part.ArcOfCircle(Part.Circle(V(0,0,0), V(0,0,1), rf), a + th_base, a + step - th_base))  # root
pad = body.newObject("PartDesign::Pad", "GearPad")
pad.Profile = gear
pad.Length = FACE
doc.recompute()

# --- Web recesses on both faces (annulus between hub and rim) ---------------
depth = (FACE - WEB) / 2
for name, z, rev in (("TopRecess", FACE, False), ("BottomRecess", 0.0, True)):
    s = new_sketch(name + "Sketch", z)
    s.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), RIM_ID / 2))
    s.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), HUB_D / 2))
    p = body.newObject("PartDesign::Pocket", name)
    p.Profile = s
    p.Length = depth
    p.Reversed = rev
    doc.recompute()

# --- Lightening holes: 6 on the hole circle, first centered on +X ----------
hs = new_sketch("LighteningHoleSketch", FACE)
for k in range(HOLES):
    a = 2 * math.pi * k / HOLES
    hs.addGeometry(Part.Circle(V(HOLE_PCD / 2 * math.cos(a), HOLE_PCD / 2 * math.sin(a), 0), V(0, 0, 1), HOLE_D / 2))
hole = body.newObject("PartDesign::Pocket", "LighteningHoles")
hole.Profile = hs
hole.Type = 1
doc.recompute()

# --- Bore with keyway on +Y ---------------------------------------------------
r = BORE_D / 2
hw = KEY_W / 2
ya = math.sqrt(r * r - hw * hw)              # where keyway sides meet the bore circle
bs = new_sketch("BoreKeywaySketch", FACE)
start = math.atan2(ya, hw)                   # angle of right keyway corner on bore
bs.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), r), math.pi - start, 2 * math.pi + start))
bs.addGeometry(Part.LineSegment(V(hw, ya, 0), V(hw, KEY_TOP, 0)))
bs.addGeometry(Part.LineSegment(V(hw, KEY_TOP, 0), V(-hw, KEY_TOP, 0)))
bs.addGeometry(Part.LineSegment(V(-hw, KEY_TOP, 0), V(-hw, ya, 0)))
bore = body.newObject("PartDesign::Pocket", "BoreKeyway")
bore.Profile = bs
bore.Type = 1
doc.recompute()

body.Tip = bore
doc.recompute()
s = body.Shape
bb = s.BoundBox
print("SOLIDS", len(s.Solids), "VALID", s.isValid())
print("VOLUME %.4f AREA %.4f" % (s.Volume, s.Area))
print("BBOX %.3f x %.3f x %.3f" % (bb.XLength, bb.YLength, bb.ZLength))
doc.saveAs(os.environ.get("OUT", "/out/reference.FCStd"))
