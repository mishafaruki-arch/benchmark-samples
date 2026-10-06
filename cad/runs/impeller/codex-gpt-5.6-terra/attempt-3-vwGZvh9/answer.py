"""Parametric radial impeller model for FreeCAD 1.1.

Run this file with FreeCAD's Python interpreter.  It writes answer.FCStd next
to this script, independently of the process working directory.
"""
import os
import FreeCAD as App
import Part


OUT_FILE = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
DOC_NAME = "RadialImpeller"


def length(obj, name, value, group="Dimensions"):
    obj.addProperty("App::PropertyLength", name, group)
    setattr(obj, name, value)


def make_feature(body, name, label, params, kind):
    """Make a named PartDesign history feature and link it to Parameters."""
    feat = body.newObject("PartDesign::Feature", name)
    feat.Label = label
    feat.addProperty("App::PropertyLink", "Parameters", "Design")
    feat.Parameters = params
    feat.addProperty("App::PropertyString", "FeatureType", "Design")
    feat.FeatureType = kind
    return feat


doc = App.newDocument(DOC_NAME)
body = doc.addObject("PartDesign::Body", "ImpellerBody")
body.Label = "Radial Impeller (single solid)"

# This is intentionally a Body member rather than a spreadsheet outside the
# model: these named properties are the authoritative editable dimensions.
params = body.newObject("PartDesign::Feature", "Parameters")
params.Label = "Impeller Parameters (mm)"
params.addProperty("App::PropertyString", "Description", "Design")
params.Description = "Master dimensions for the radial impeller"
length(params, "backplate_diameter", 120.0)
length(params, "backplate_thickness", 4.0)
length(params, "hub_diameter", 30.0)
length(params, "overall_height", 36.0)
params.addProperty("App::PropertyInteger", "number_of_blades", "Dimensions")
params.number_of_blades = 7
length(params, "blade_height", 20.0)
length(params, "blade_tip_diameter", 116.0)
length(params, "bore_diameter", 10.0)
# Explicit blade construction dimensions, retained as editable metadata.
length(params, "blade_inner_arc_radius", 48.5, "Blade profile")
length(params, "blade_outer_arc_radius", 51.5, "Blade profile")
length(params, "blade_arc_center_y", 50.0, "Blade profile")
length(params, "blade_thickness", 3.0, "Blade profile")
length(params, "bore_flat_x", 4.0, "Bore")

P = App.Vector
bp_r = params.backplate_diameter.Value / 2.0
hub_r = params.hub_diameter.Value / 2.0
tip_r = params.blade_tip_diameter.Value / 2.0
plate_h = params.backplate_thickness.Value
blade_h = params.blade_height.Value

# Base feature: back face is exactly on the XY plane.
backplate = make_feature(body, "BackPlate", "Back plate (Ø120 x 4)", params,
                         "Additive cylinder / base feature")
length(backplate, "Diameter", params.backplate_diameter.Value, "Back plate")
length(backplate, "Thickness", params.backplate_thickness.Value, "Back plate")
backplate.Shape = Part.makeCylinder(bp_r, plate_h, P(0, 0, 0))
backplate.addProperty("App::PropertyString", "ZExtent", "Back plate")
backplate.ZExtent = "0 mm to 4 mm"

# Hub history feature: a cylinder followed by a conical frustum, with a flat
# top at overall_height.  It is fused to the preceding plate feature.
hub = make_feature(body, "Hub", "Hub cylinder and taper", params,
                   "Additive cylinder + additive cone")
length(hub, "CylinderDiameter", params.hub_diameter.Value, "Hub")
length(hub, "CylinderHeight", 24.0, "Hub")
length(hub, "TopDiameter", 16.0, "Hub")
length(hub, "OverallHeight", params.overall_height.Value, "Hub")
hub_cylinder = Part.makeCylinder(hub_r, 24.0, P(0, 0, plate_h))
hub_cone = Part.makeCone(hub_r, 8.0, params.overall_height.Value - 28.0,
                         P(0, 0, 28.0))
hub.Shape = backplate.Shape.fuse(hub_cylinder.fuse(hub_cone)).removeSplitter()

# Build the first backward-curved strip by booleaning the two concentric
# cylinders, the X>=0 half-space, the tip circle, and the outside of the hub.
# This produces exact circular arc boundaries, then each blade is placed by a
# Z-axis rotation in its own parametric PartDesign history feature.
annulus_outer = Part.makeCylinder(params.blade_outer_arc_radius.Value, blade_h,
                                  P(0, params.blade_arc_center_y.Value, plate_h))
annulus_inner = Part.makeCylinder(params.blade_inner_arc_radius.Value, blade_h,
                                  P(0, params.blade_arc_center_y.Value, plate_h))
annulus = annulus_outer.cut(annulus_inner)
x_positive = Part.makeBox(80.0, 140.0, blade_h, P(0, -40, plate_h))
tip_limit = Part.makeCylinder(tip_r, blade_h, P(0, 0, plate_h))
hub_exclusion = Part.makeCylinder(hub_r, blade_h, P(0, 0, plate_h))
first_blade = annulus.common(x_positive).common(tip_limit).cut(hub_exclusion)

running_shape = hub.Shape
for i in range(params.number_of_blades):
    angle = 360.0 * i / params.number_of_blades
    blade_solid = first_blade.copy()
    blade_solid.rotate(P(0, 0, 0), P(0, 0, 1), angle)
    blade = make_feature(body, "Blade%02d" % (i + 1),
                         "Blade %d (%g deg)" % (i + 1, angle), params,
                         "Additive curved blade")
    blade.addProperty("App::PropertyInteger", "BladeIndex", "Blade")
    blade.BladeIndex = i + 1
    blade.addProperty("App::PropertyAngle", "Rotation", "Blade")
    blade.Rotation = angle
    length(blade, "Height", blade_h, "Blade")
    length(blade, "StripThickness", params.blade_thickness.Value, "Blade")
    blade.addProperty("App::PropertyString", "Profile", "Blade")
    blade.Profile = "R48.5/R51.5 centered at (0,50); X>=0; tip Ø116"
    running_shape = running_shape.fuse(blade_solid).removeSplitter()
    blade.Shape = running_shape

# Final subtractive feature.  The box intersection retains X <= 4 of the
# Ø10 cylinder, making the prescribed D profile with its flat on +X.
bore = make_feature(body, "D_Bore", "D-shaped through bore", params,
                    "Subtractive pocket (through all)")
length(bore, "Diameter", params.bore_diameter.Value, "Bore")
length(bore, "FlatX", params.bore_flat_x.Value, "Bore")
bore.addProperty("App::PropertyString", "Direction", "Bore")
bore.Direction = "Z axis, through all"
bore_cylinder = Part.makeCylinder(params.bore_diameter.Value / 2.0, 40.0,
                                  P(0, 0, -1.0))
keep_left_of_flat = Part.makeBox(14.0, 20.0, 40.0, P(-10.0, -10.0, -1.0))
d_bore = bore_cylinder.common(keep_left_of_flat)
bore.Shape = running_shape.cut(d_bore).removeSplitter()

# Keep a conventional feature-tree presentation: only the final tip is shown.
for obj in body.Group:
    obj.Visibility = False
bore.Visibility = True
body.Tip = bore

doc.recompute()
Gui = getattr(App, "GuiUp", False)
doc.recompute()
doc.saveAs(OUT_FILE)
print("Saved", OUT_FILE)
