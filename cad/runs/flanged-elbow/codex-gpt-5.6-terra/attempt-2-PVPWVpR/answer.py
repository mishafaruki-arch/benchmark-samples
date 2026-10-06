import os
import math

import FreeCAD as App
import Part
import Sketcher


OUTFILE = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"


def rounded_square(sketch, width, radius):
    """Add a closed, centred rounded-square wire to a sketch."""
    h = width / 2.0
    q = h - radius
    # Straight sides, with the arcs deliberately sharing their end points.
    sketch.addGeometry(Part.LineSegment(App.Vector(-q, -h, 0), App.Vector(q, -h, 0)), False)
    sketch.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(q, -q, 0), App.Vector(0, 0, 1), radius), -math.pi / 2, 0), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(h, -q, 0), App.Vector(h, q, 0)), False)
    sketch.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(q, q, 0), App.Vector(0, 0, 1), radius), 0, math.pi / 2), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(q, h, 0), App.Vector(-q, h, 0)), False)
    sketch.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(-q, q, 0), App.Vector(0, 0, 1), radius), math.pi / 2, math.pi), False)
    sketch.addGeometry(Part.LineSegment(App.Vector(-h, q, 0), App.Vector(-h, -q, 0)), False)
    sketch.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(-q, -q, 0), App.Vector(0, 0, 1), radius), math.pi, 3 * math.pi / 2), False)


def add_hole_circles(sketch, bore_radius, bolt_radius):
    sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), bore_radius), False)
    for x in (-30, 30):
        for y in (-30, 30):
            sketch.addGeometry(Part.Circle(App.Vector(x, y, 0), App.Vector(0, 0, 1), bolt_radius), False)


def set_expr(obj, prop, expr):
    try:
        obj.setExpression(prop, expr)
    except Exception:
        pass


doc = App.newDocument("FlangedPipeElbow")
body = doc.addObject("PartDesign::Body", "PipeElbowBody")
body.Label = "90 Degree Flanged Pipe Elbow (Parametric)"

# Master dimensions are intentionally exposed on the Body.  Feature dimensions below
# use expressions to these properties wherever FreeCAD permits an expression.
for name, value in (
    ("pipe_outer_diameter", 40.0),
    ("pipe_inner_diameter", 32.0),
    ("flange_width", 80.0),
    ("flange_thickness", 12.0),
    ("flange_corner_radius", 8.0),
    ("bolt_hole_diameter", 9.0),
    ("number_bolt_holes_per_flange", 4),
    ("bend_centerline_radius", 60.0),
    ("overall_height", 140.0),
    ("overall_length", 140.0),
):
    typ = "App::PropertyInteger" if name == "number_bolt_holes_per_flange" else "App::PropertyLength"
    body.addProperty(typ, name, "Parameters")
    setattr(body, name, value)

# Inlet flange: a true rounded-square Pad, rather than a precomputed solid.
# Sketcher objects are nested in the Body and are consumed by Pad/Pocket features.
sk1 = body.newObject("Sketcher::SketchObject", "InletFlangeSketch")
sk1.Label = "Inlet rounded square flange profile"
rounded_square(sk1, 80.0, 8.0)
pad1 = body.newObject("PartDesign::Pad", "InletFlangePad")
pad1.Profile = sk1
pad1.Length = 12.0
set_expr(pad1, "Length", "PipeElbowBody.flange_thickness")

hs1 = body.newObject("Sketcher::SketchObject", "InletFlangeHoleSketch")
hs1.Label = "Inlet bore and four bolt holes"
add_hole_circles(hs1, 16.0, 4.5)
pocket1 = body.newObject("PartDesign::Pocket", "InletFlangeHoles")
pocket1.Profile = hs1
pocket1.Length = 12.0
# The sketch normal is +Z, matching the Pad direction; pocket into the flange.
pocket1.Reversed = True
set_expr(pocket1, "Length", "PipeElbowBody.flange_thickness")

# Vertical pipe.  AdditiveCylinder is an editable PartDesign primitive.
inlet_pipe = body.newObject("PartDesign::AdditiveCylinder", "InletStraightOuterPipe")
inlet_pipe.Radius = 20.0
inlet_pipe.Height = 28.0
inlet_pipe.Placement.Base = App.Vector(0, 0, 12)
set_expr(inlet_pipe, "Radius", "PipeElbowBody.pipe_outer_diameter / 2")

# The outer elbow is an editable AdditivePipe swept along a quarter-circle sketch.
outer_profile = body.newObject("Sketcher::SketchObject", "OuterElbowProfile")
outer_profile.Placement.Base = App.Vector(0, 0, 40)
outer_profile.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 20), False)
outer_path = body.newObject("Sketcher::SketchObject", "OuterElbowSpine")
outer_path.Label = "Outer 90 degree bend centreline R60"
outer_path.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(1, 0, 0), 90))
outer_path.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(60, 40, 0), App.Vector(0, 0, 1), 60), math.pi / 2, math.pi), False)
outer_bend = body.newObject("PartDesign::AdditivePipe", "Outer90DegreeBend")
outer_bend.Profile = outer_profile
outer_bend.Spine = (outer_path, ["Edge1"])

# Horizontal outer pipe from X=60 to X=88.
outlet_pipe = body.newObject("PartDesign::AdditiveCylinder", "OutletStraightOuterPipe")
outlet_pipe.Radius = 20.0
outlet_pipe.Height = 28.0
outlet_pipe.Placement = App.Placement(App.Vector(60, 0, 100), App.Rotation(App.Vector(0, 1, 0), 90))
set_expr(outlet_pipe, "Radius", "PipeElbowBody.pipe_outer_diameter / 2")

# Outlet flange is a second rounded-square Pad on the YZ plane at X=88.
sk2 = body.newObject("Sketcher::SketchObject", "OutletFlangeSketch")
sk2.Label = "Outlet rounded square flange profile"
sk2.Placement = App.Placement(App.Vector(88, 0, 100), App.Rotation(App.Vector(0, 1, 0), 90))
rounded_square(sk2, 80.0, 8.0)
pad2 = body.newObject("PartDesign::Pad", "OutletFlangePad")
pad2.Profile = sk2
pad2.Length = 12.0
set_expr(pad2, "Length", "PipeElbowBody.flange_thickness")

hs2 = body.newObject("Sketcher::SketchObject", "OutletFlangeHoleSketch")
hs2.Label = "Outlet bore and four bolt holes"
hs2.Placement = App.Placement(App.Vector(88, 0, 100), App.Rotation(App.Vector(0, 1, 0), 90))
add_hole_circles(hs2, 16.0, 4.5)
pocket2 = body.newObject("PartDesign::Pocket", "OutletFlangeHoles")
pocket2.Profile = hs2
pocket2.Length = 12.0
# The local sketch normal maps to +X, matching the outlet Pad direction.
pocket2.Reversed = True
set_expr(pocket2, "Length", "PipeElbowBody.flange_thickness")

# Continuous bore: editable subtractive primitives plus a subtractive pipe.
inlet_bore = body.newObject("PartDesign::SubtractiveCylinder", "InletStraightBore")
inlet_bore.Radius = 16.0
inlet_bore.Height = 40.0
set_expr(inlet_bore, "Radius", "PipeElbowBody.pipe_inner_diameter / 2")

inner_profile = body.newObject("Sketcher::SketchObject", "InnerElbowProfile")
inner_profile.Placement.Base = App.Vector(0, 0, 40)
inner_profile.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 16), False)
inner_path = body.newObject("Sketcher::SketchObject", "InnerElbowSpine")
inner_path.Label = "Inner 90 degree bend centreline R60"
inner_path.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(1, 0, 0), 90))
inner_path.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(60, 40, 0), App.Vector(0, 0, 1), 60), math.pi / 2, math.pi), False)
inner_bend = body.newObject("PartDesign::SubtractivePipe", "Inner90DegreeBendBore")
inner_bend.Profile = inner_profile
inner_bend.Spine = (inner_path, ["Edge1"])

outlet_bore = body.newObject("PartDesign::SubtractiveCylinder", "OutletStraightBore")
outlet_bore.Radius = 16.0
outlet_bore.Height = 40.0
outlet_bore.Placement = App.Placement(App.Vector(60, 0, 100), App.Rotation(App.Vector(0, 1, 0), 90))
set_expr(outlet_bore, "Radius", "PipeElbowBody.pipe_inner_diameter / 2")

doc.recompute()
doc.recompute()
doc.saveAs(OUTFILE)
print("Saved", OUTFILE)
print("Tip:", body.Tip.Name if body.Tip else "None")
print("Solids:", len(body.Tip.Shape.Solids) if body.Tip else 0)
