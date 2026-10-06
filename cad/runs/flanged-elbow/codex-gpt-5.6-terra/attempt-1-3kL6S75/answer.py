"""Parametric 90 degree flanged pipe elbow for FreeCAD 1.1.

Run this file with FreeCAD's Python interpreter.  The model is deliberately
made from PartDesign features (rather than importing a final BRep shape).
"""
from pathlib import Path
import math

import FreeCAD as App
import Part
import Sketcher


OUTFILE = Path(__file__).with_suffix(".FCStd")
doc = App.newDocument("FlangedPipeElbow")


def setexpr(obj, prop, expr):
    """Set an expression after the target property has been made visible."""
    obj.setExpression(prop, expr)


def place(obj, base, rotation=None):
    obj.Placement = App.Placement(App.Vector(*base), rotation or App.Rotation())


body = doc.addObject("PartDesign::Body", "ElbowBody")
body.Label = "90 degree flanged pipe elbow (parametric)"

# A non-geometric parameter carrier avoids a Body-to-child expression cycle.
# It has no Shape; every feature that makes the sole solid is in ElbowBody.
params = doc.addObject("App::FeaturePython", "Parameters")
params.Label = "Elbow dimensional parameters"

# These inputs remain editable after saving and are referenced by all the
# dimensional PartDesign features below.
parameters = (
    ("pipe_outer_diameter", "Pipe outer diameter", 40.0),
    ("pipe_inner_diameter", "Pipe inner diameter", 32.0),
    ("flange_width", "Flange square width", 80.0),
    ("flange_thickness", "Flange thickness", 12.0),
    ("flange_corner_radius", "Rounded flange corner radius", 8.0),
    ("bolt_hole_diameter", "Bolt hole diameter", 9.0),
    ("bend_centerline_radius", "Bend centerline radius", 60.0),
    ("inlet_straight_length", "Inlet straight length above flange", 28.0),
    ("outlet_straight_length", "Outlet straight length", 28.0),
    ("overall_height", "Overall bounding height", 140.0),
    ("overall_length", "Overall bounding length", 140.0),
)
for name, label, value in parameters:
    params.addProperty("App::PropertyLength", name, "Dimensions", label)
    setattr(params, name, value)
params.addProperty("App::PropertyInteger", "number_bolt_holes_per_flange", "Dimensions",
                 "Number of bolt holes on each flange")
params.number_bolt_holes_per_flange = 4


def additive_box(name, label, base, rotation=None):
    o = body.newObject("PartDesign::AdditiveBox", name)
    o.Label = label
    place(o, base, rotation)
    return o


def rounded_box(previous, name, label):
    # On PartDesign boxes edges 1,3,5,7 are parallel to the primitive's local
    # Height direction: the four through-thickness corners.
    f = body.newObject("PartDesign::Fillet", name)
    f.Label = label
    f.Base = (previous, ["Edge1", "Edge3", "Edge5", "Edge7"])
    f.Radius = 8.0
    setexpr(f, "Radius", "Parameters.flange_corner_radius")
    return f


# Inlet flange: square on XY, thickness along Z.
inlet_box = additive_box("InletFlangeBlock", "Inlet flange square", (-40, -40, 0))
inlet_box.Length = 80
inlet_box.Width = 80
inlet_box.Height = 12
setexpr(inlet_box, "Length", "Parameters.flange_width")
setexpr(inlet_box, "Width", "Parameters.flange_width")
setexpr(inlet_box, "Height", "Parameters.flange_thickness")
inlet_flange = rounded_box(inlet_box, "InletFlangeFillet", "Inlet flange rounded corners")


# A profile and a three-edge spine form one editable additive sweep.  The
# profile starts at Z=0 so it fuses to the inlet flange.  The spine describes
# the requested Z straight, R60 quarter-circle, and +X outlet straight.
# Actual profile sketch is retained as an editable document object.
outer_sketch = body.newObject("Sketcher::SketchObject", "OuterPipeProfile")
outer_sketch.Label = "Outer pipe circular profile"
outer_sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 20), False)
outer_sketch.addConstraint(Sketcher.Constraint("Diameter", 0, 40.0))
setexpr(outer_sketch, "Constraints[0]", "Parameters.pipe_outer_diameter")
outer_sketch.Visibility = False

spine = body.newObject("Sketcher::SketchObject", "OuterPipeSpine")
spine.Label = "Pipe centreline: straight, R60 bend, straight"
# Sketch XY is rotated so local Y is global Z, putting its geometry in XZ.
place(spine, (0, 0, 0), App.Rotation(App.Vector(1, 0, 0), 90))
spine.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(0, 40, 0)), False)
# In local X,Y = global X,Z, the arc goes (0,40) -> (60,100).
spine.addGeometry(Part.Arc(App.Vector(0, 40, 0),
                            App.Vector(60 - 60 / math.sqrt(2), 40 + 60 / math.sqrt(2), 0),
                            App.Vector(60, 100, 0)), False)
spine.addGeometry(Part.LineSegment(App.Vector(60, 100, 0), App.Vector(100, 100, 0)), False)
spine.addProperty("App::PropertyLength", "BendRadius", "Parameters")
spine.BendRadius = 60.0
setexpr(spine, "BendRadius", "Parameters.bend_centerline_radius")
spine.Visibility = False

outer_pipe = body.newObject("PartDesign::AdditivePipe", "OuterPipeSweep")
outer_pipe.Label = "Outer pipe additive sweep"
outer_pipe.Profile = outer_sketch
outer_pipe.Spine = (spine, ["Edge1", "Edge2", "Edge3"])


# Outlet flange is the same rounded square, rotated so its thickness is +X.
# This 120 degree rotation maps primitive local (X,Y,Z) to global (Y,Z,X).
outlet_rot = App.Rotation(App.Vector(1, 1, 1), 120)
outlet_box = additive_box("OutletFlangeBlock", "Outlet flange square", (88, -40, 60), outlet_rot)
outlet_box.Length = 80
outlet_box.Width = 80
outlet_box.Height = 12
setexpr(outlet_box, "Length", "Parameters.flange_width")
setexpr(outlet_box, "Width", "Parameters.flange_width")
setexpr(outlet_box, "Height", "Parameters.flange_thickness")
outlet_flange = rounded_box(outlet_box, "OutletFlangeFillet", "Outlet flange rounded corners")


# Remove the continuous bore with the matching editable subtractive sweep.
inner_sketch = body.newObject("Sketcher::SketchObject", "BoreProfile")
inner_sketch.Label = "Continuous bore circular profile"
inner_sketch.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 16), False)
inner_sketch.addConstraint(Sketcher.Constraint("Diameter", 0, 32.0))
setexpr(inner_sketch, "Constraints[0]", "Parameters.pipe_inner_diameter")
inner_sketch.Visibility = False

inner_spine = body.newObject("Sketcher::SketchObject", "BoreSpine")
inner_spine.Label = "Bore centreline"
place(inner_spine, (0, 0, 0), App.Rotation(App.Vector(1, 0, 0), 90))
inner_spine.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(0, 40, 0)), False)
inner_spine.addGeometry(Part.Arc(App.Vector(0, 40, 0),
                                  App.Vector(60 - 60 / math.sqrt(2), 40 + 60 / math.sqrt(2), 0),
                                  App.Vector(60, 100, 0)), False)
inner_spine.addGeometry(Part.LineSegment(App.Vector(60, 100, 0), App.Vector(100, 100, 0)), False)
inner_spine.Visibility = False

bore = body.newObject("PartDesign::SubtractivePipe", "ContinuousBore")
bore.Label = "Continuous pipe bore subtractive sweep"
bore.Profile = inner_sketch
bore.Spine = (inner_spine, ["Edge1", "Edge2", "Edge3"])


def bolt_hole(name, label, base, rotation=None):
    h = body.newObject("PartDesign::SubtractiveCylinder", name)
    h.Label = label
    h.Radius = 4.5
    h.Height = 12.0
    setexpr(h, "Radius", "Parameters.bolt_hole_diameter / 2")
    setexpr(h, "Height", "Parameters.flange_thickness")
    place(h, base, rotation)
    return h


# Inlet bolt axes are +Z. Outlet axes are +X; rotate cylinder local Z to +X.
for i, (x, y) in enumerate(((-30, -30), (-30, 30), (30, -30), (30, 30)), 1):
    bolt_hole("InletBoltHole%02d" % i, "Inlet bolt hole %d" % i, (x, y, 0))

to_x = App.Rotation(App.Vector(0, 1, 0), 90)
for i, (y, z) in enumerate(((-30, 70), (-30, 130), (30, 70), (30, 130)), 1):
    bolt_hole("OutletBoltHole%02d" % i, "Outlet bolt hole %d" % i, (88, y, z), to_x)

doc.recompute()

# Keep only the final solid visible; all preceding items remain editable in the tree.
for obj in body.Group:
    if obj != body.Tip:
        obj.Visibility = False
body.Tip.Visibility = True
doc.recompute()
doc.saveAs(str(OUTFILE))
