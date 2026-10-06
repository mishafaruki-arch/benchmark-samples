"""Build the splined stepped drive shaft and save it beside this script.

The construction deliberately keeps each manufacturing operation as a named
PartDesign feature.  Numeric properties on those features are the design
parameters retained in the FCStd file.
"""
import os
import FreeCAD as App
import Part


DOC_NAME = "SplinedDriveShaft"


def quantity(obj, name, value, group="Parameters"):
    obj.addProperty("App::PropertyLength", name, group)
    setattr(obj, name, value)


def integer(obj, name, value, group="Parameters"):
    obj.addProperty("App::PropertyInteger", name, group)
    setattr(obj, name, value)


def clean(shape):
    """Refine boolean results when the kernel can do so."""
    try:
        return shape.removeSplitter()
    except Exception:
        return shape


doc = App.newDocument(DOC_NAME)
body = doc.addObject("PartDesign::Body", "DriveShaftBody")
body.Label = "Splined Stepped Drive Shaft (single solid)"

# 1. The outside stepped profile is a true revolved profile, including both
# end chamfers.  Coordinates are (radius, Z) in the XZ plane.
base = body.newObject("PartDesign::Feature", "BaseRevolution")
base.Label = "Base Revolution (stepped shaft)"
quantity(base, "OverallLength", 175.0)
quantity(base, "SplineMajorDiameter", 25.0)
quantity(base, "BearingDiameter", 30.0)
quantity(base, "CollarDiameter", 40.0)
quantity(base, "EndDiameter", 20.0)
quantity(base, "EndChamfer", 1.0)

pts = [
    App.Vector(0, 0, 0), App.Vector(11.5, 0, 0),
    App.Vector(12.5, 0, 1), App.Vector(12.5, 0, 40),
    App.Vector(15, 0, 40), App.Vector(15, 0, 90),
    App.Vector(20, 0, 90), App.Vector(20, 0, 100),
    App.Vector(15, 0, 100), App.Vector(15, 0, 140),
    App.Vector(10, 0, 140), App.Vector(10, 0, 174),
    App.Vector(9, 0, 175), App.Vector(0, 0, 175),
    App.Vector(0, 0, 0),
]
profile = Part.Face(Part.makePolygon(pts))
base.Shape = profile.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)

# 2. Retaining ring groove, 2 mm wide in the first bearing journal.
groove = body.newObject("PartDesign::Feature", "RetainingRingGroove")
groove.Label = "Retaining-ring groove (82-84 mm)"
quantity(groove, "StartZ", 82.0)
quantity(groove, "Width", 2.0)
quantity(groove, "GrooveDiameter", 28.0)
quantity(groove, "BearingDiameter", 30.0)
# Only the annular material between the 30 mm journal and the 28 mm groove
# floor is removed; a full cylinder here would incorrectly sever the shaft.
groove_cut = Part.makeCylinder(15.1, 2.0, App.Vector(0, 0, 82)).cut(
    Part.makeCylinder(14.0, 2.0, App.Vector(0, 0, 82))
)
groove.Shape = clean(base.Shape.cut(groove_cut))

# 3. Spline spaces.  The retained section is a 21 mm core plus six 6 mm
# straight-sided teeth.  The tooth tips include the 1 mm end chamfer.
spline = body.newObject("PartDesign::Feature", "SplineTeeth")
spline.Label = "6 straight-sided spline teeth"
quantity(spline, "SplineMajorDiameter", 25.0)
quantity(spline, "SplineMinorDiameter", 21.0)
integer(spline, "NumberOfSplines", 6)
quantity(spline, "SplineLength", 30.0)
quantity(spline, "ToothWidth", 6.0)
quantity(spline, "EndChamfer", 1.0)

core = Part.makeCylinder(10.5, 30.0)
tooth_section = Part.makeBox(15.0, 6.0, 29.0, App.Vector(0, -3, 1))
tooth_outer = Part.makeCylinder(12.5, 29.0, App.Vector(0, 0, 1)).common(tooth_section)
tooth_tip_section = Part.makeBox(15.0, 6.0, 1.0, App.Vector(0, -3, 0))
tooth_tip = Part.makeCone(11.5, 12.5, 1.0).common(tooth_tip_section)
retained_spline = core.fuse(tooth_outer.fuse(tooth_tip))
for angle in range(60, 360, 60):
    # Rotation is made on a copy to preserve the prototype tooth.
    t = tooth_outer.fuse(tooth_tip).copy()
    t.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), angle)
    retained_spline = retained_spline.fuse(t)
space_blank = Part.makeCylinder(13.0, 30.0)
spline_spaces = space_blank.cut(retained_spline)
spline.Shape = clean(groove.Shape.cut(spline_spaces))

# 4. Rounded-end axial keyway, extruded radially inward to the X=6.5 floor.
keyway = body.newObject("PartDesign::Feature", "Keyway")
keyway.Label = "6 mm rounded-end keyway"
quantity(keyway, "Width", 6.0)
quantity(keyway, "FloorX", 6.5)
quantity(keyway, "Depth", 3.5)
quantity(keyway, "FirstEndCenterZ", 148.0)
quantity(keyway, "SecondEndCenterZ", 167.0)
quantity(keyway, "EndRadius", 3.0)
key_box = Part.makeBox(15.0, 6.0, 19.0, App.Vector(6.5, -3.0, 148.0))
end_a = Part.makeCylinder(3.0, 15.0, App.Vector(6.5, 0, 148.0), App.Vector(1, 0, 0))
end_b = Part.makeCylinder(3.0, 15.0, App.Vector(6.5, 0, 167.0), App.Vector(1, 0, 0))
keyway.Shape = clean(spline.Shape.cut(key_box.fuse(end_a).fuse(end_b)))

# 5. Cross drilled hole through the second bearing journal, along Y.
cross = body.newObject("PartDesign::Feature", "CrossHole")
cross.Label = "5 mm cross hole (Y axis)"
quantity(cross, "Diameter", 5.0)
quantity(cross, "CenterZ", 120.0)
cross.addProperty("App::PropertyString", "Axis", "Parameters")
cross.Axis = "Y"
cross_hole = Part.makeCylinder(2.5, 40.0, App.Vector(0, -20, 120), App.Vector(0, 1, 0))
cross.Shape = clean(keyway.Shape.cut(cross_hole))

doc.recompute()

# Explicitly leave the Body tip at the final editable operation.
body.Tip = cross
doc.recompute()

out_path = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
doc.recompute()
doc.saveAs(out_path)
print(out_path)
