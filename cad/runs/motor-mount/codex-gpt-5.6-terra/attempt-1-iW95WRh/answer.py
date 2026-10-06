import os
import math

import FreeCAD as App
import Part
import Sketcher


# This file intentionally creates ordinary PartDesign operations (rather than
# importing a finished BREP), so the dimensions below remain editable in the
# saved document.
doc = App.newDocument("MotorMount")
body = doc.addObject("PartDesign::Body", "MotorMountBody")
body.Label = "Motor Mount (single solid)"
params = doc.addObject("App::FeaturePython", "Parameters")
params.Label = "Motor Mount Parameters"

def parameter(name, value, label=None):
    params.addProperty("App::PropertyLength", name, "Dimensions", label or name)
    setattr(params, name, value)

parameter("overall_length", 110.0)
parameter("overall_width", 62.0)
parameter("plate_thickness", 25.0)
parameter("bore_diameter", 50.25)
parameter("corner_radius", 3.5)
params.addProperty("App::PropertyInteger", "number_mounting_holes", "Dimensions")
params.number_mounting_holes = 4
parameter("mounting_hole_pcd", 70.0)
parameter("front_hole_diameter", 4.2)
parameter("front_hole_depth", 11.138)
parameter("back_hole_diameter", 3.3)
parameter("back_hole_depth", 9.109)
parameter("ear_hole_diameter", 5.5)
parameter("ear_hole_center_y", 51.0)
parameter("ear_hole_z_lower", 6.5)
parameter("ear_hole_z_upper", 18.5)
params.addProperty("App::PropertyAngle", "drill_point_angle", "Dimensions")
params.drill_point_angle = 118.0

def add_line(sk, a, b):
    sk.addGeometry(Part.LineSegment(App.Vector(*a, 0), App.Vector(*b, 0)), False)

sk = body.newObject("Sketcher::SketchObject", "OuterProfileSketch")
sk.Label = "Outer C plate profile (sharp before rounds)"
pts = [(-30,-30),(22,-30),(22,-55),(32,-55),(32,-25),(27,-20),
       (27,20),(32,25),(32,55),(22,55),(22,30),(-30,30)]
for a, b in zip(pts, pts[1:] + pts[:1]):
    add_line(sk, a, b)

pad = body.newObject("PartDesign::Pad", "PlatePad")
pad.Profile = sk
pad.Length = 25
pad.setExpression("Length", "Parameters.plate_thickness")
pad.ReferenceAxis = (sk, ["N_Axis"])
pad.Midplane = False
pad.Reversed = False
doc.recompute()

# Circular motor bore, then an opening to the right which makes it a C-shape.
bore_sk = body.newObject("Sketcher::SketchObject", "MotorBoreSketch")
bore_sk.Placement.Base.z = 0
bore_sk.addGeometry(Part.Circle(App.Vector(0,0,0), App.Vector(0,0,1), 25.125), False)
# Radius constraint is expression driven by the named body parameter.
bore_sk.addConstraint(Sketcher.Constraint("Radius", 0, 25.125))
bore_sk.setExpression("Constraints[0]", "Parameters.bore_diameter / 2")
bore = body.newObject("PartDesign::Pocket", "MotorBorePocket")
bore.Profile = bore_sk
bore.Length = 30
bore.Type = 1  # Through all
bore.Reversed = True
doc.recompute()

slot_sk = body.newObject("Sketcher::SketchObject", "BoreOpeningSketch")
slot_sk.Placement.Base.z = 0
for a,b in [((0,-20),(27,-20)),((27,-20),(27,20)),((27,20),(0,20)),((0,20),(0,-20))]:
    add_line(slot_sk,a,b)
opening = body.newObject("PartDesign::Pocket", "BoreOpeningPocket")
opening.Profile = slot_sk
opening.Length = 30
opening.Type = 1
opening.Reversed = True
doc.recompute()

def vertical_edges_at(shape, targets, tol=0.03):
    """Return EdgeN strings for vertical edges located at the requested XY points."""
    found = []
    for i, e in enumerate(shape.Edges, 1):
        bb = e.BoundBox
        if bb.ZLength < 24.9 or bb.XLength > 0.03 or bb.YLength > 0.03:
            continue
        x, y = (bb.XMin + bb.XMax)/2, (bb.YMin + bb.YMax)/2
        if any((x-a)**2 + (y-b)**2 < tol*tol for a,b in targets):
            found.append("Edge%d" % i)
    return found

# Apply the specified 3.5-mm vertical-edge rounds.  The bore/slot crossings
# are calculated from the actual bore radius so their edge selections survive
# a parameter change followed by rebuilding this script.
r = 50.25 / 2
ix = math.sqrt(r*r - 20*20)
large_targets = [(-30,-30),(-30,30),(22,-30),(22,30),(32,-25),(32,25),
                 (27,-20),(27,20),(ix,-20),(ix,20)]
large_edges = vertical_edges_at(opening.Shape, large_targets)
if len(large_edges) != 10:
    candidates = []
    for i,e in enumerate(opening.Shape.Edges,1):
        bb=e.BoundBox
        if bb.ZLength > 24.9 and bb.XLength < .03 and bb.YLength < .03:
            candidates.append((i, round((bb.XMin+bb.XMax)/2,3),round((bb.YMin+bb.YMax)/2,3)))
    raise RuntimeError("Could not identify all large-radius vertical edges: %r all=%r" % (large_edges,candidates))
round_big = body.newObject("PartDesign::Fillet", "MainCornerRounds")
round_big.Base = (opening, large_edges)
round_big.Radius = 3.5
round_big.setExpression("Radius", "Parameters.corner_radius")
doc.recompute()

small_targets = [(22,-55),(32,-55),(22,55),(32,55)]
small_edges = vertical_edges_at(round_big.Shape, small_targets)
if len(small_edges) != 4:
    raise RuntimeError("Could not identify ear-end vertical edges: %r" % small_edges)
round_small = body.newObject("PartDesign::Fillet", "EarEndCornerRounds")
round_small.Base = (round_big, small_edges)
round_small.Radius = 0.5
doc.recompute()

def subtract_cylinder(name, label, radius_expr, height_expr, base, axis):
    f = body.newObject("PartDesign::SubtractiveCylinder", name)
    f.Label = label
    f.Radius = 1
    f.Height = 1
    f.setExpression("Radius", radius_expr)
    f.setExpression("Height", height_expr)
    f.Placement = App.Placement(App.Vector(*base), App.Rotation(App.Vector(0,0,1), App.Vector(*axis)))
    doc.recompute()
    return f

def subtract_cone(name, label, radius_expr, height_expr, base, axis):
    f = body.newObject("PartDesign::SubtractiveCone", name)
    f.Label = label
    f.Radius1 = 1
    f.Radius2 = 0
    f.Height = 1
    f.setExpression("Radius1", radius_expr)
    f.setExpression("Height", height_expr)
    f.Placement = App.Placement(App.Vector(*base), App.Rotation(App.Vector(0,0,1), App.Vector(*axis)))
    doc.recompute()
    return f

# Four front/back blind tap drillings, including their 118-degree drill points.
tip_front = (4.2/2) / math.tan(math.radians(59))
tip_back = (3.3/2) / math.tan(math.radians(59))
last = round_small
for n, deg in enumerate((45,135,225,315), 1):
    a = math.radians(deg)
    x, y = 35*math.cos(a), 35*math.sin(a)
    last = subtract_cylinder("FrontHoleCylinder%d" % n, "Front blind drilling %d cylinder" % n,
                             "Parameters.front_hole_diameter / 2", "Parameters.front_hole_depth", (x,y,0), (0,0,1))
    last = subtract_cone("FrontHolePoint%d" % n, "Front blind drilling %d 118deg point" % n,
                         "Parameters.front_hole_diameter / 2", str(tip_front), (x,y,11.138), (0,0,1))
    last = subtract_cylinder("BackHoleCylinder%d" % n, "Back blind drilling %d cylinder" % n,
                             "Parameters.back_hole_diameter / 2", "Parameters.back_hole_depth", (x,y,25), (0,0,-1))
    last = subtract_cone("BackHolePoint%d" % n, "Back blind drilling %d 118deg point" % n,
                         "Parameters.back_hole_diameter / 2", str(tip_back), (x,y,25-9.109), (0,0,-1))

# Four transverse ear holes. Cylinders are along +X and cut the full 10-mm ear width.
for n, (yy, zz) in enumerate(((51,6.5),(51,18.5),(-51,6.5),(-51,18.5)), 1):
    last = subtract_cylinder("EarHole%d" % n, "Ear through hole %d" % n,
                             "Parameters.ear_hole_diameter / 2", "10 mm", (22,yy,zz), (1,0,0))

doc.recompute()
if not last.Shape.isValid() or last.Shape.Solids.__len__() != 1:
    raise RuntimeError("Result is not a single valid solid")

out_path = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
doc.recompute()
doc.saveAs(out_path)
print(out_path)
