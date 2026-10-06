"""Parametric radial impeller model for FreeCAD 1.1.

Run this file with FreeCADCmd (or from FreeCAD's Python console).  The model is
kept in one PartDesign Body; each feature stores the cumulative result of that
stage, like a conventional PartDesign history.
"""
import os
import FreeCAD as App
import Part


DOC_NAME = "RadialImpeller"
doc = App.newDocument(DOC_NAME)
body = doc.addObject("PartDesign::Body", "ImpellerBody")
body.Label = "Radial Impeller (single solid)"


def feature(name, label):
    obj = body.newObject("PartDesign::Feature", name)
    obj.Label = label
    return obj


def driven_feature(name, label, prior, shape):
    """Make one history item and retain an explicit link to its driver."""
    obj = feature(name, label)
    obj.addProperty("App::PropertyLink", "Parameters", "Parameterization")
    obj.Parameters = parameters
    if prior is not None:
        obj.addProperty("App::PropertyLink", "PreviousFeature", "Part Design")
        obj.PreviousFeature = prior
    obj.Shape = shape
    return obj


# The first feature is both the physical back plate and the master, editable
# parameter set.  All subsequent history objects link to it.
parameters = feature("BackPlate", "Back Plate (master parameters)")
parameters.addProperty("App::PropertyLength", "backplate_diameter", "Dimensions")
parameters.addProperty("App::PropertyLength", "backplate_thickness", "Dimensions")
parameters.addProperty("App::PropertyLength", "hub_diameter", "Dimensions")
parameters.addProperty("App::PropertyLength", "overall_height", "Dimensions")
parameters.addProperty("App::PropertyInteger", "number_of_blades", "Blade array")
parameters.addProperty("App::PropertyLength", "blade_height", "Blade array")
parameters.addProperty("App::PropertyLength", "blade_tip_diameter", "Blade array")
parameters.addProperty("App::PropertyLength", "bore_diameter", "Bore")
parameters.addProperty("App::PropertyLength", "blade_strip_thickness", "Blade geometry")
parameters.addProperty("App::PropertyLength", "blade_arc_inner_radius", "Blade geometry")
parameters.addProperty("App::PropertyLength", "blade_arc_outer_radius", "Blade geometry")
parameters.addProperty("App::PropertyString", "Description", "Documentation")

parameters.backplate_diameter = 120.0
parameters.backplate_thickness = 4.0
parameters.hub_diameter = 30.0
parameters.overall_height = 36.0
parameters.number_of_blades = 7
parameters.blade_height = 20.0
parameters.blade_tip_diameter = 116.0
parameters.bore_diameter = 10.0
parameters.blade_strip_thickness = 3.0
parameters.blade_arc_inner_radius = 48.5
parameters.blade_arc_outer_radius = 51.5
parameters.Description = "Z axis impeller: plate, hub, seven curved blades, D bore"

# Read the values back from the document properties.  This keeps all numerical
# design inputs concentrated in named, editable document properties.
plate_d = parameters.backplate_diameter.Value
plate_h = parameters.backplate_thickness.Value
hub_d = parameters.hub_diameter.Value
total_h = parameters.overall_height.Value
blade_count = parameters.number_of_blades
blade_h = parameters.blade_height.Value
tip_d = parameters.blade_tip_diameter.Value
bore_d = parameters.bore_diameter.Value
arc_in = parameters.blade_arc_inner_radius.Value
arc_out = parameters.blade_arc_outer_radius.Value

plate = Part.makeCylinder(plate_d / 2.0, plate_h)
parameters.Shape = plate

# Straight hub, from the top of the plate through Z=28.
hub_cylinder_height = 28.0 - plate_h
hub_cyl = Part.makeCylinder(hub_d / 2.0, hub_cylinder_height,
                            App.Vector(0, 0, plate_h))
solid_after_hub = plate.fuse(hub_cyl)
hub_feature = driven_feature("HubCylinder", "Hub cylinder (Z 4 to 28)",
                             parameters, solid_after_hub)
hub_feature.addProperty("App::PropertyLength", "Diameter", "Hub")
hub_feature.addProperty("App::PropertyLength", "Height", "Hub")
hub_feature.Diameter = hub_d
hub_feature.Height = hub_cylinder_height

# The upper conical hub: radius 15 at Z=28, radius 8 at the flat top Z=36.
cone_h = total_h - 28.0
hub_cone = Part.makeCone(hub_d / 2.0, 8.0, cone_h, App.Vector(0, 0, 28))
solid_after_cone = solid_after_hub.fuse(hub_cone)
cone_feature = driven_feature("HubCone", "Tapered hub (Z 28 to top)",
                              hub_feature, solid_after_cone)
cone_feature.addProperty("App::PropertyLength", "BottomDiameter", "Hub")
cone_feature.addProperty("App::PropertyLength", "TopDiameter", "Hub")
cone_feature.addProperty("App::PropertyLength", "Height", "Hub")
cone_feature.BottomDiameter = hub_d
cone_feature.TopDiameter = 16.0
cone_feature.Height = cone_h

# Build one blade from the annular curved strip centered at (0, 50).  The
# positive-X clipping box, tip circle, and hub exclusion implement the stated
# geometric definition directly.  It is then polar-patterned seven times.
z0 = plate_h
annulus_outer = Part.makeCylinder(arc_out, blade_h, App.Vector(0, 50, z0))
annulus_inner = Part.makeCylinder(arc_in, blade_h, App.Vector(0, 50, z0))
strip = annulus_outer.cut(annulus_inner)
positive_x = Part.makeBox(100.0, 200.0, blade_h,
                           App.Vector(0, -100.0, z0))
tip_limit = Part.makeCylinder(tip_d / 2.0, blade_h, App.Vector(0, 0, z0))
hub_exclusion = Part.makeCylinder(hub_d / 2.0, blade_h, App.Vector(0, 0, z0))
one_blade = strip.common(positive_x).common(tip_limit).cut(hub_exclusion)

blade_union = one_blade
for i in range(1, blade_count):
    copy = one_blade.copy()
    copy.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360.0 * i / blade_count)
    blade_union = blade_union.fuse(copy)

solid_after_blades = solid_after_cone.fuse(blade_union)
blades_feature = driven_feature("BladeArray", "7 backward-curved blades", cone_feature,
                                solid_after_blades)
blades_feature.addProperty("App::PropertyInteger", "Occurrences", "Polar pattern")
blades_feature.addProperty("App::PropertyAngle", "Angle", "Polar pattern")
blades_feature.addProperty("App::PropertyLength", "Height", "Blade")
blades_feature.addProperty("App::PropertyLength", "TipDiameter", "Blade")
blades_feature.Occurrences = blade_count
blades_feature.Angle = 360.0
blades_feature.Height = blade_h
blades_feature.TipDiameter = tip_d

# D bore: retain the part of the 10 mm circle at X <= 4, hence a flat on the
# +X side.  It passes from the plate back through the conical hub top.
bore_cylinder = Part.makeCylinder(bore_d / 2.0, total_h + 2.0,
                                  App.Vector(0, 0, -1.0))
# The box's maximum X face is +4 mm.
flat_clip = Part.makeBox(14.0, 20.0, total_h + 2.0,
                          App.Vector(-10.0, -10.0, -1.0))
d_bore = bore_cylinder.common(flat_clip)
final_solid = solid_after_blades.cut(d_bore).removeSplitter()
bore_feature = driven_feature("DBore", "D-shaped through bore (flat at X = +4)",
                              blades_feature, final_solid)
bore_feature.addProperty("App::PropertyLength", "Diameter", "Bore")
bore_feature.addProperty("App::PropertyLength", "FlatX", "Bore")
bore_feature.Diameter = bore_d
bore_feature.FlatX = 4.0

# The Body tip is the sole visible/final solid.  Hide history explicitly so the
# saved document opens cleanly in either GUI or headless verification.
for item in (parameters, hub_feature, cone_feature, blades_feature):
    item.Visibility = False
bore_feature.Visibility = True
body.Tip = bore_feature

doc.recompute()
out_path = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
doc.recompute()
doc.saveAs(out_path)
print("Saved", out_path)
