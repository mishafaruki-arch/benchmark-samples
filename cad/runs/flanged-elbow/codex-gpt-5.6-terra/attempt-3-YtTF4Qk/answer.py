"""Parametric feature-tree model of a flanged 90 degree pipe elbow.

Run with FreeCADCmd.  The output file is deliberately located from this
script, so it does not depend on FreeCAD's current working directory.
"""
import os
import FreeCAD as App
import Part


OUTFILE = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
doc = App.newDocument("FlangedPipeElbow")
body = doc.addObject("PartDesign::Body", "FlangedPipeElbowBody")
body.Label = "90 degree flanged pipe elbow (single solid)"

# This is a real document object (inside the Body) rather than script-local
# constants.  It provides a convenient, editable design table in FreeCAD.
params = body.newObject("PartDesign::Feature", "DesignParameters")
params.Label = "Design parameters (mm)"

def length(name, value, text):
    params.addProperty("App::PropertyLength", name, "Dimensions", text)
    setattr(params, name, value)

length("pipe_outer_diameter", 40.0, "Outside diameter of pipe")
length("pipe_inner_diameter", 32.0, "Continuous bore diameter")
length("flange_width", 80.0, "Overall square flange width")
length("flange_thickness", 12.0, "Thickness of each flange")
length("flange_corner_radius", 8.0, "Radius at flange corners")
length("bolt_hole_diameter", 9.0, "Diameter of bolt holes")
params.addProperty("App::PropertyInteger", "number_bolt_holes_per_flange", "Dimensions",
                   "Number of holes in each flange")
params.number_bolt_holes_per_flange = 4
length("bend_centerline_radius", 60.0, "Elbow centreline radius")
length("overall_height", 140.0, "Bounding height")
length("overall_length", 140.0, "Bounding length")
params.addProperty("App::PropertyString", "Description", "Documentation")
params.Description = "90 degree elbow: inlet +Z, then quarter bend toward +X"


def rounded_inlet_flange(w, r, t):
    """Rounded 80 x 80 plate, from z=0 to z=t, centered on z axis."""
    # Two overlapping rectangles plus the four corner cylinders gives an exact
    # rounded-square outline and is especially robust in the OCCT kernel.
    s = w / 2.0 - r
    result = Part.makeBox(w - 2*r, w, t, App.Vector(-s, -w/2, 0))
    result = result.fuse(Part.makeBox(w, w - 2*r, t, App.Vector(-w/2, -s, 0)))
    for x in (-s, s):
        for y in (-s, s):
            result = result.fuse(Part.makeCylinder(r, t, App.Vector(x, y, 0)))
    return result


def rounded_outlet_flange(w, r, t):
    """Rounded square plate perpendicular to X, x=88 through x=100."""
    x0, zc = 88.0, 100.0
    s = w / 2.0 - r
    result = Part.makeBox(t, w - 2*r, w, App.Vector(x0, -s, zc-w/2))
    result = result.fuse(Part.makeBox(t, w, w - 2*r, App.Vector(x0, -w/2, zc-s)))
    for y in (-s, s):
        for z in (zc-s, zc+s):
            result = result.fuse(Part.makeCylinder(r, t, App.Vector(x0, y, z), App.Vector(1, 0, 0)))
    return result


def pipe_sweep(radius):
    """Quarter-circle solid, from (0,0,40) tangent +Z to (60,0,100) tangent +X."""
    start = App.Vector(0, 0, 40)
    mid = App.Vector(60 - 60/(2**0.5), 0, 40 + 60/(2**0.5))
    end = App.Vector(60, 0, 100)
    spine = Part.Wire([Part.Arc(start, mid, end).toShape()])
    # At the start the tangent is +Z, hence the circle lies in the XY plane.
    profile = Part.Wire([Part.makeCircle(radius, start, App.Vector(0, 0, 1))])
    return spine.makePipeShell([profile], True, False)


def feature(name, label, shape, previous=None):
    obj = body.newObject("PartDesign::Feature", name)
    obj.Label = label
    if previous is not None:
        obj.BaseFeature = previous
    obj.Shape = shape
    return obj


# Read values from the persisted parameter feature, not from duplicate literals.
od = params.pipe_outer_diameter.Value
id_ = params.pipe_inner_diameter.Value
w = params.flange_width.Value
t = params.flange_thickness.Value
cr = params.flange_corner_radius.Value
bh = params.bolt_hole_diameter.Value
ro, ri = od/2.0, id_/2.0

# Additive PartDesign feature sequence.  Every feature stores the accumulated
# result, as PartDesign Tips normally do, and the last feature is the sole Body tip.
inlet_flange = feature("InletFlange", "Additive inlet rounded-square flange",
                       rounded_inlet_flange(w, cr, t))
inlet_flange.addProperty("App::PropertyLink", "Parameters", "Feature")
inlet_flange.Parameters = params

inlet_pipe_solid = Part.makeCylinder(ro, 40.0-t, App.Vector(0, 0, t))
inlet_pipe = feature("InletStraightPipe", "Additive inlet straight pipe (Z)",
                     inlet_flange.Shape.fuse(inlet_pipe_solid), inlet_flange)

elbow_outer = pipe_sweep(ro)
elbow = feature("NinetyDegreeElbow", "Additive 90 degree swept elbow",
                inlet_pipe.Shape.fuse(elbow_outer), inlet_pipe)
elbow.addProperty("App::PropertyLength", "centerline_radius", "Sweep")
elbow.centerline_radius = params.bend_centerline_radius

outlet_pipe_solid = Part.makeCylinder(ro, 28.0, App.Vector(60, 0, 100), App.Vector(1, 0, 0))
outlet_pipe = feature("OutletStraightPipe", "Additive outlet straight pipe (X)",
                      elbow.Shape.fuse(outlet_pipe_solid), elbow)

outlet_flange = feature("OutletFlange", "Additive outlet rounded-square flange",
                         outlet_pipe.Shape.fuse(rounded_outlet_flange(w, cr, t)), outlet_pipe)

# One continuous subtractive bore.  It includes the central openings of both
# flanges and every straight/bent pipe segment.
bore = Part.makeCylinder(ri, 40.0, App.Vector(0, 0, 0))
bore = bore.fuse(pipe_sweep(ri))
bore = bore.fuse(Part.makeCylinder(ri, 40.0, App.Vector(60, 0, 100), App.Vector(1, 0, 0)))
bore_cut = feature("ContinuousBore", "Subtractive continuous pipe bore",
                   outlet_flange.Shape.cut(bore), outlet_flange)
bore_cut.addProperty("App::PropertyLength", "diameter", "Pocket")
bore_cut.diameter = params.pipe_inner_diameter

# Four holes on the 60 mm square in each flange, all as one parametric pocket.
holes = None
for x in (-30.0, 30.0):
    for y in (-30.0, 30.0):
        h = Part.makeCylinder(bh/2.0, t, App.Vector(x, y, 0))
        holes = h if holes is None else holes.fuse(h)
for y in (-30.0, 30.0):
    for z in (70.0, 130.0):
        h = Part.makeCylinder(bh/2.0, t, App.Vector(88, y, z), App.Vector(1, 0, 0))
        holes = holes.fuse(h)
final = feature("FlangeBoltHoles", "Subtractive bolt-hole pocket (8 holes)",
                bore_cut.Shape.cut(holes), bore_cut)
final.addProperty("App::PropertyLength", "diameter", "Pocket")
final.diameter = params.bolt_hole_diameter
final.addProperty("App::PropertyInteger", "holes_per_flange", "Pocket")
final.holes_per_flange = params.number_bolt_holes_per_flange

body.Tip = final
doc.recompute()

# Refine removes Boolean splitter faces without changing topology or dimensions.
final.Shape = final.Shape.removeSplitter()
doc.recompute()
doc.recompute()
doc.saveAs(OUTFILE)
print("Saved", OUTFILE)
