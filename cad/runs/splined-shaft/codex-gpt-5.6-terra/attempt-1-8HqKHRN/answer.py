"""Parametric PartDesign model of the splined stepped drive shaft.

Run with FreeCAD's Python interpreter.  The output is deliberately located
beside this source file, so it is independent of the launch directory.
"""
import os
import FreeCAD as App


DOC_NAME = "SplinedDriveShaft"
doc = App.newDocument(DOC_NAME)

# A spreadsheet is deliberately used as the expression source, rather than
# putting expressions back onto the Body itself (which creates a dependency
# cycle between a Body and its features).
sheet = doc.addObject("Spreadsheet::Sheet", "Parameters")
sheet.Label = "Drive shaft parameters (mm)"

# The body is the only solid-producing container in the document.  Keeping the
# driving values on it makes them visible and editable in the Data panel.
body = doc.addObject("PartDesign::Body", "DriveShaftBody")
body.Label = "Splined stepped drive shaft (parametric)"

parameters = (
    ("overall_length", 175.0),
    ("spline_major_diameter", 25.0),
    ("spline_minor_diameter", 21.0),
    ("number_of_splines", 6),
    ("spline_length", 30.0),
    ("bearing_diameter", 30.0),
    ("collar_diameter", 40.0),
    ("groove_diameter", 28.0),
    ("end_diameter", 20.0),
    ("keyway_depth", 3.5),
    ("cross_hole_diameter", 5.0),
)
for name, value in parameters:
    typ = "App::PropertyInteger" if name == "number_of_splines" else "App::PropertyLength"
    body.addProperty(typ, name, "Dimensions")
    setattr(body, name, value)
    row = len(sheet.getNonEmptyCells()) + 1
    sheet.set("A%d" % row, name)
    sheet.set("B%d" % row, ("%d" % value) if name == "number_of_splines" else ("%s mm" % value))
    sheet.setAlias("B%d" % row, name)

# Useful fixed manufacturing dimensions are also explicit editable parameters.
for name, value in (("end_chamfer", 1.0), ("groove_width", 2.0),
                    ("spline_tooth_width", 6.0), ("keyway_width", 6.0)):
    body.addProperty("App::PropertyLength", name, "Dimensions")
    setattr(body, name, value)
    row = len(sheet.getNonEmptyCells()) + 1
    sheet.set("A%d" % row, name)
    sheet.set("B%d" % row, "%s mm" % value)
    sheet.setAlias("B%d" % row, name)


def at(obj, x=0, y=0, z=0, axis=None, angle=0):
    """Set a primitive's placement without introducing external supports."""
    rotation = App.Rotation() if axis is None else App.Rotation(App.Vector(*axis), angle)
    obj.Placement = App.Placement(App.Vector(x, y, z), rotation)


def add_cylinder(name, label, radius_expr, height_expr, z_expr, x=0, y=0,
                 axis=None, angle=0):
    obj = body.newObject("PartDesign::AdditiveCylinder", name)
    obj.Label = label
    obj.setExpression("Radius", radius_expr)
    obj.setExpression("Height", height_expr)
    at(obj, x, y, 0, axis, angle)
    obj.setExpression("Placement.Base.z", z_expr)
    return obj


def add_cone(name, label, r1, r2, height, z):
    obj = body.newObject("PartDesign::AdditiveCone", name)
    obj.Label = label
    obj.setExpression("Radius1", r1)
    obj.setExpression("Radius2", r2)
    obj.setExpression("Height", height)
    obj.setExpression("Placement.Base.z", z)
    return obj


def cut_cylinder(name, label, radius_expr, height_expr, x=0, y=0, z=0,
                 axis=None, angle=0):
    obj = body.newObject("PartDesign::SubtractiveCylinder", name)
    obj.Label = label
    obj.setExpression("Radius", radius_expr)
    obj.setExpression("Height", height_expr)
    at(obj, x, y, z, axis, angle)
    return obj


def cut_box(name, label, lx, ly, lz, x, y, z, rotation=0):
    obj = body.newObject("PartDesign::SubtractiveBox", name)
    obj.Label = label
    obj.Length = lx
    obj.Width = ly
    obj.Height = lz
    at(obj, x, y, z, (0, 0, 1), rotation)
    return obj


# Additive revolved/primitive sequence.  The two cones are the 1 x 45 degree
# end chamfers; the remaining primitives are the sharp stepped shaft sections.
add_cone("SplineEndChamfer", "Spline-end 1 mm x 45 deg chamfer",
         "(Parameters.spline_major_diameter / 2) - Parameters.end_chamfer",
         "Parameters.spline_major_diameter / 2", "Parameters.end_chamfer", "0 mm")
add_cylinder("SplineMajorStep", "Spline major diameter step",
             "Parameters.spline_major_diameter / 2", "39 mm", "1 mm")
add_cylinder("BearingStepA", "First bearing diameter step",
             "Parameters.bearing_diameter / 2", "50 mm", "40 mm")
add_cylinder("Collar", "Collar diameter step",
             "Parameters.collar_diameter / 2", "10 mm", "90 mm")
add_cylinder("BearingStepB", "Second bearing diameter step",
             "Parameters.bearing_diameter / 2", "40 mm", "100 mm")
add_cylinder("KeyedEndStep", "Keyed-end diameter step",
             "Parameters.end_diameter / 2", "Parameters.overall_length - 141 mm", "140 mm")
add_cone("KeyedEndChamfer", "Keyed-end 1 mm x 45 deg chamfer",
         "Parameters.end_diameter / 2",
         "(Parameters.end_diameter / 2) - Parameters.end_chamfer",
         "Parameters.end_chamfer", "Parameters.overall_length - Parameters.end_chamfer")

# Six straight-sided teeth are made by pocketing the spaces down to the minor
# diameter.  Each tooth has two pockets, one on each flat side.  This retains a
# circular root at the specified minor diameter and a circular 25 mm major OD.
spline_count = int(body.number_of_splines)
for tooth in range(spline_count):
    angle = tooth * (360.0 / spline_count)
    for side, y in (("Plus", 3.0), ("Minus", -20.0)):
        # Local X begins exactly at the minor radius; local Y limits are the
        # two planes 3 mm either side of the tooth radial centre plane.
        cut_box("SplineSpace_%d_%s" % (tooth + 1, side),
                "Spline space %d %s side" % (tooth + 1, side),
                12.0, 17.0, 30.0, 10.5, y, 0.0, angle)

# Retaining-ring groove, Z=82..84.  A ring is represented by 24 editable
# radial pocket boxes.  This avoids a coaxial subtractive cylinder (which would
# incorrectly bore out the centre and split the shaft into two solids), while
# producing a near-circular 28 mm groove floor with a fully connected core.
for sector in range(24):
    groove = cut_box("RetainingGrooveSector_%02d" % (sector + 1),
                     "Retaining groove sector %02d" % (sector + 1),
                     10.0, 40.0, 2.0, 14.0, -20.0, 82.0, sector * 15.0)
    groove.setExpression("Placement.Base.x", "Parameters.groove_diameter / 2")
    groove.setExpression("Height", "Parameters.groove_width")

# Keyway capsule: central radial slot plus two radius-3 end cutters.  The
# cylinder axes are X, creating rounded ends in the Y-Z plane.
key_box = cut_box("KeywayStraight", "Keyway straight section", 20.0, 6.0, 19.0,
                  6.5, -3.0, 148.0)
key_box.setExpression("Length", "Parameters.end_diameter")
key_box.setExpression("Width", "Parameters.keyway_width")
for name, z in (("KeywayRoundEndA", 148.0), ("KeywayRoundEndB", 167.0)):
    cut_cylinder(name, name.replace("Keyway", "Keyway rounded "), "3 mm",
                 "Parameters.end_diameter", x=6.5, y=0, z=z,
                 axis=(0, 1, 0), angle=90)

# Through cross hole, axis Y, centred at Z=120 on the shaft axis.
cut_cylinder("CrossHole", "Cross hole, diameter 5 mm", "Parameters.cross_hole_diameter / 2",
             "50 mm", x=0, y=-25, z=120, axis=(1, 0, 0), angle=-90)

doc.recompute()

# A compact description is useful when inspecting the document without having
# to reverse-engineer every primitive in the tree.
body.addProperty("App::PropertyString", "DesignNotes", "Documentation")
body.DesignNotes = "Six spline teeth; groove Z=82..84; keyway capsule Z=145..170; cross-hole Z=120."

out_path = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
doc.recompute()
doc.saveAs(out_path)
print(out_path)
