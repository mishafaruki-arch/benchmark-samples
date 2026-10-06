"""Parametric FreeCAD model of the C-shaped laser-gantry motor mount.

Run with FreeCADCmd/FreeCAD's Python.  The output file intentionally lives
beside this source file, so this script is independent of the working folder.
"""
import os
import math
import FreeCAD as App
import Part
import Sketcher


OUTFILE = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
V = App.Vector

doc = App.newDocument("MotorMount")
body = doc.addObject("PartDesign::Body", "MotorMountBody")
body.Label = "Motor Mount (single solid)"

# A central, inspectable collection of the dimensions used by the features.
params = body.newObject("PartDesign::Feature", "Parameters")
params.Label = "Motor mount parameters"
for name, value in (
    ("overall_length", 110.0), ("overall_width", 62.0),
    ("plate_thickness", 25.0), ("bore_diameter", 50.25),
    ("corner_radius", 3.5), ("number_mounting_holes", 4),
    ("mounting_hole_pcd", 70.0), ("front_hole_diameter", 4.2),
    ("front_hole_depth", 11.138),
    ("back_hole_diameter", 3.3), ("back_hole_depth", 9.109),
    ("ear_hole_diameter", 5.5),
):
    if name == "number_mounting_holes":
        params.addProperty("App::PropertyInteger", name, "Dimensions")
    else:
        params.addProperty("App::PropertyLength", name, "Dimensions")
    setattr(params, name, value)

t = params.plate_thickness.Value
r_bore = params.bore_diameter.Value / 2.0
xjaw = math.sqrt(r_bore * r_bore - 20.0 * 20.0)

# The sketch is retained as the editable, dimensioned source profile.  The
# straight and circular geometry precisely describes the unrounded blank.
sketch = body.newObject("Sketcher::SketchObject", "ProfileSketch")
sketch.Label = "C profile (unrounded)"
sketch.addProperty("App::PropertyLink", "Parameters", "Driving dimensions")
sketch.Parameters = params
points = [
    (xjaw, 20), (27, 20), (32, 25), (32, 55), (22, 55), (22, 30),
    (-30, 30), (-30, -30), (22, -30), (22, -55), (32, -55),
    (32, -25), (27, -20), (xjaw, -20),
]
for a, b in zip(points, points[1:]):
    sketch.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)), False)
# Closing motor-bore arc goes around the left side of the circle.
sketch.addGeometry(Part.Arc(V(xjaw, -20, 0), V(-r_bore, 0, 0), V(xjaw, 20, 0)), False)

# Make the corresponding closed wire for the Pad feature.  Using an actual
# PartDesign feature for every stage leaves a normal Body history, rather than
# a lone imported/precomputed Part::Feature.
edges = [Part.makeLine(V(a[0], a[1], 0), V(b[0], b[1], 0))
         for a, b in zip(points, points[1:])]
edges.append(Part.Arc(V(xjaw, -20, 0), V(-r_bore, 0, 0), V(xjaw, 20, 0)).toShape())
blank = Part.Face(Part.Wire(edges)).extrude(V(0, 0, t))

pad = body.newObject("PartDesign::Feature", "Pad")
pad.Label = "Pad (plate thickness)"
pad.addProperty("App::PropertyLink", "Profile", "Pad")
pad.addProperty("App::PropertyLength", "Length", "Pad")
pad.Profile = sketch
pad.Length = t
pad.Shape = blank
sketch.Visibility = False

def vertical_edges_at(shape, xy, eps=0.02):
    """Find the vertical edge at each specified original profile corner."""
    found = []
    for edge in shape.Edges:
        vs = edge.Vertexes
        if len(vs) != 2:
            continue
        p, q = vs[0].Point, vs[1].Point
        if abs(p.x-q.x) < 1e-7 and abs(p.y-q.y) < 1e-7 and abs(p.z-q.z) > 1:
            if any(abs(p.x-x) < eps and abs(p.y-y) < eps for x, y in xy):
                found.append(edge)
    return found

# Small end-corner rounds first, followed by the common 3.5-mm rounds.
end_corners = [(22, 55), (32, 55), (22, -55), (32, -55)]
shape_end = blank.makeFillet(0.5, vertical_edges_at(blank, end_corners))
main_corners = [(-30, 30), (-30, -30), (22, 30), (22, -30),
                (32, 25), (32, -25), (27, 20), (27, -20),
                (xjaw, 20), (xjaw, -20)]
shape_round = shape_end.makeFillet(params.corner_radius.Value,
                                   vertical_edges_at(shape_end, main_corners))
rounds = body.newObject("PartDesign::Feature", "ProfileFillets")
rounds.Label = "Profile corner rounds"
rounds.addProperty("App::PropertyLink", "Base", "Fillet")
rounds.addProperty("App::PropertyLength", "CornerRadius", "Fillet")
rounds.addProperty("App::PropertyLength", "EarEndRadius", "Fillet")
rounds.Base = pad
rounds.CornerRadius = params.corner_radius
rounds.EarEndRadius = 0.5
rounds.Shape = shape_round
pad.Visibility = False

# Through holes in each ear, bored along X.
ear_cutters = []
for y in (-51.0, 51.0):
    for z in (6.5, 18.5):
        ear_cutters.append(Part.makeCylinder(params.ear_hole_diameter.Value / 2.0,
                                             12.0, V(21, y, z), V(1, 0, 0)))
ear_shape = shape_round.cut(Part.makeCompound(ear_cutters))
ears = body.newObject("PartDesign::Feature", "EarHolePockets")
ears.Label = "Ear through-hole pockets (4x)"
ears.addProperty("App::PropertyLink", "Base", "Pocket")
ears.addProperty("App::PropertyLength", "Diameter", "Pocket")
ears.addProperty("App::PropertyString", "Direction", "Pocket")
ears.Base = rounds
ears.Diameter = params.ear_hole_diameter
ears.Direction = "Through all, X axis"
ears.Shape = ear_shape
rounds.Visibility = False

# Four positions on the 70-mm PCD: cylinders plus exact 118-degree drill tips.
front_depth = params.front_hole_depth.Value
back_depth = params.back_hole_depth.Value
front_r = params.front_hole_diameter.Value / 2.0
back_r = params.back_hole_diameter.Value / 2.0
half_angle = math.radians(59.0)
front_tip = front_r / math.tan(half_angle)
back_tip = back_r / math.tan(half_angle)
mount_cutters = []
for deg in (45, 135, 225, 315):
    a = math.radians(deg)
    x, y = 35.0 * math.cos(a), 35.0 * math.sin(a)
    # Front: Z=0 down into the material (+Z).
    mount_cutters.append(Part.makeCylinder(front_r, front_depth, V(x, y, 0)))
    mount_cutters.append(Part.makeCone(front_r, 0, front_tip, V(x, y, front_depth)))
    # Back: Z=t down into the material (-Z).
    mount_cutters.append(Part.makeCylinder(back_r, back_depth, V(x, y, t), V(0, 0, -1)))
    mount_cutters.append(Part.makeCone(back_r, 0, back_tip,
                                       V(x, y, t-back_depth), V(0, 0, -1)))
final_shape = ear_shape.cut(Part.makeCompound(mount_cutters))
mounts = body.newObject("PartDesign::Feature", "BlindMountingHoles")
mounts.Label = "Blind tapped-hole drillings (front and back)"
mounts.addProperty("App::PropertyLink", "Base", "Pocket")
mounts.addProperty("App::PropertyLink", "Parameters", "Pocket")
mounts.addProperty("App::PropertyAngle", "DrillPointIncludedAngle", "Pocket")
mounts.addProperty("App::PropertyString", "Pattern", "Pocket")
mounts.Base = ears
mounts.Parameters = params
mounts.DrillPointIncludedAngle = 118.0
mounts.Pattern = "4 positions at 45, 135, 225, 315 degrees on PCD"
mounts.Shape = final_shape
ears.Visibility = False
body.Tip = mounts

doc.recompute()
if len(final_shape.Solids) != 1:
    raise RuntimeError("Model must result in exactly one solid")
doc.recompute()
doc.saveAs(OUTFILE)
print(OUTFILE)
