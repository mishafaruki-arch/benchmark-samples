"""Parametric webbed 36 tooth spur gear for FreeCAD 1.1.

Run with FreeCADCmd (or from FreeCAD's Python console).  The document is
written next to this file, rather than relative to FreeCAD's working folder.
"""
import math
import os

import FreeCAD as App
import Part


OUT_FILE = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"


def polar(radius, angle, z=0.0):
    return App.Vector(radius * math.cos(angle), radius * math.sin(angle), z)


def involute_point(base_radius, t, start_angle, side):
    """Point on an involute, with side +1 or -1 of the tooth centreline."""
    # Polar angular advance of an involute is t - atan(t).
    angle = side * (start_angle + t - math.atan(t))
    radius = base_radius * math.sqrt(1.0 + t * t)
    return polar(radius, angle)


def make_tooth(root_radius, base_radius, tip_radius, tooth_half_angle,
               pitch_radius):
    """A closed tooth face, including radial sub-base flanks and circular tip."""
    tp = math.sqrt((pitch_radius / base_radius) ** 2 - 1.0)
    tt = math.sqrt((tip_radius / base_radius) ** 2 - 1.0)
    # At pitch radius the flank must be exactly half a tooth thickness from
    # the centreline.  This fixes the involute's base-circle start angle.
    start = tooth_half_angle - (tp - math.atan(tp))

    right_base = polar(base_radius, start)
    left_base = polar(base_radius, -start)
    right_root = polar(root_radius, start)
    left_root = polar(root_radius, -start)

    samples = 25
    right_curve = [involute_point(base_radius, tt * i / samples, start, 1)
                   for i in range(samples + 1)]
    left_curve = [involute_point(base_radius, tt * i / samples, start, -1)
                  for i in range(samples + 1)]
    right_spline = Part.BSplineCurve()
    right_spline.interpolate(right_curve)
    left_spline = Part.BSplineCurve()
    left_spline.interpolate(list(reversed(left_curve)))

    right_tip = right_curve[-1]
    left_tip = left_curve[-1]
    # Both arcs pass through the centreline (+X), so the selected arcs are
    # the short tip/root arcs, not their complementary major arcs.
    tip_arc = Part.Arc(right_tip, polar(tip_radius, 0), left_tip).toShape()
    root_arc = Part.Arc(left_root, polar(root_radius, 0), right_root).toShape()
    edges = [Part.makeLine(right_root, right_base), right_spline.toShape(),
             tip_arc, left_spline.toShape(), Part.makeLine(left_base, left_root),
             root_arc]
    return Part.Face(Part.Wire(edges))


def add_length(obj, name, value, group="Gear parameters"):
    obj.addProperty("App::PropertyLength", name, group)
    setattr(obj, name, value)


def add_int(obj, name, value, group="Gear parameters"):
    obj.addProperty("App::PropertyInteger", name, group)
    setattr(obj, name, value)


def add_angle(obj, name, value, group="Gear parameters"):
    obj.addProperty("App::PropertyAngle", name, group)
    setattr(obj, name, value)


def feature(body, name, label, source=None):
    obj = body.newObject("PartDesign::Feature", name)
    obj.Label = label
    if source is not None:
        obj.addProperty("App::PropertyLink", "SourceFeature", "Dependency")
        obj.SourceFeature = source
        source.Visibility = False
    return obj


doc = App.newDocument("WebbedSpurGear")
body = doc.addObject("PartDesign::Body", "GearBody")
body.Label = "Webbed Spur Gear (PartDesign Body)"

# This feature is the editable parameter carrier for the complete gear.
blank = feature(body, "GearBlank", "01 Gear blank and involute teeth")
add_length(blank, "GearModule", 2.0)
add_int(blank, "NumberOfTeeth", 36)
add_angle(blank, "PressureAngle", 20.0, "Tooth geometry")
add_length(blank, "TipDiameter", 76.0)
add_length(blank, "RootDiameter", 67.0)
add_length(blank, "FaceWidth", 20.0)
add_length(blank, "RimInnerDiameter", 56.0, "Web geometry")
add_length(blank, "HubDiameter", 30.0, "Web geometry")
add_length(blank, "WebThickness", 8.0, "Web geometry")
blank.addProperty("App::PropertyString", "ProfileDescription", "Tooth geometry")
blank.ProfileDescription = "20 degree full-depth involute; tooth centered on +X"

module = blank.GearModule.Value
teeth = blank.NumberOfTeeth
face_width = blank.FaceWidth.Value
pitch_radius = module * teeth / 2.0
base_radius = pitch_radius * math.cos(math.radians(blank.PressureAngle.Value))
tip_radius = blank.TipDiameter.Value / 2.0
root_radius = blank.RootDiameter.Value / 2.0
tooth = make_tooth(root_radius, base_radius, tip_radius,
                   math.pi / (2.0 * teeth), pitch_radius)
tooth_solids = []
for i in range(teeth):
    tooth_solids.append(tooth.extrude(App.Vector(0, 0, face_width)).transformGeometry(
        App.Matrix()))
    # Rotation is applied after extrusion to retain a planar, vertical tooth.
    tooth_solids[-1].rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360.0 * i / teeth)

root_solid = Part.makeCylinder(root_radius, face_width)
gear_shape = root_solid.multiFuse(tooth_solids).removeSplitter()
blank.Shape = gear_shape
blank.addProperty("App::PropertyLength", "PitchDiameter", "Derived dimensions")
blank.PitchDiameter = 2.0 * pitch_radius
blank.setEditorMode("PitchDiameter", 1)
blank.addProperty("App::PropertyLength", "BaseDiameter", "Derived dimensions")
blank.BaseDiameter = 2.0 * base_radius
blank.setEditorMode("BaseDiameter", 1)

# Equal face recesses leave an 8 mm web centred in the 20 mm face width.
top_recess = feature(body, "TopWebRecess", "02 Top annular web recess", blank)
add_length(top_recess, "RecessDepth", (face_width - blank.WebThickness.Value) / 2.0,
           "Recess parameters")
add_length(top_recess, "OuterDiameter", blank.RimInnerDiameter.Value, "Recess parameters")
add_length(top_recess, "InnerDiameter", blank.HubDiameter.Value, "Recess parameters")
rd = top_recess.RecessDepth.Value
outer = Part.makeCylinder(top_recess.OuterDiameter.Value / 2.0, rd,
                          App.Vector(0, 0, face_width - rd))
inner = Part.makeCylinder(top_recess.InnerDiameter.Value / 2.0, rd + 0.02,
                          App.Vector(0, 0, face_width - rd - 0.01))
top_recess.Shape = gear_shape.cut(outer.cut(inner)).removeSplitter()

bottom_recess = feature(body, "BottomWebRecess", "03 Bottom annular web recess", top_recess)
add_length(bottom_recess, "RecessDepth", rd, "Recess parameters")
bottom_recess.addProperty("App::PropertyString", "Symmetry", "Recess parameters")
bottom_recess.Symmetry = "Matches TopWebRecess"
outer = Part.makeCylinder(blank.RimInnerDiameter.Value / 2.0, rd, App.Vector(0, 0, 0))
inner = Part.makeCylinder(blank.HubDiameter.Value / 2.0, rd + 0.02, App.Vector(0, 0, -0.01))
web_shape = top_recess.Shape.cut(outer.cut(inner)).removeSplitter()
bottom_recess.Shape = web_shape

holes = feature(body, "LighteningHoles", "04 Six web lightening holes", bottom_recess)
add_int(holes, "NumberLighteningHoles", 6, "Hole parameters")
add_length(holes, "LighteningHoleDiameter", 10.0, "Hole parameters")
add_length(holes, "LighteningHolePCD", 43.0, "Hole parameters")
holes.addProperty("App::PropertyString", "Pattern", "Hole parameters")
holes.Pattern = "Circular; first hole centered on +X"
hole_tools = []
for i in range(holes.NumberLighteningHoles):
    a = 2.0 * math.pi * i / holes.NumberLighteningHoles
    c = polar(holes.LighteningHolePCD.Value / 2.0, a, -0.01)
    hole_tools.append(Part.makeCylinder(holes.LighteningHoleDiameter.Value / 2.0,
                                        face_width + 0.02, c))
holes.Shape = web_shape.cut(Part.makeCompound(hole_tools)).removeSplitter()

bore = feature(body, "BoreAndKeyway", "05 Through bore and 5 mm keyway", holes)
add_length(bore, "BoreDiameter", 16.0, "Bore and keyway")
add_length(bore, "KeywayWidth", 5.0, "Bore and keyway")
add_length(bore, "KeywayFloorRadius", 10.3, "Bore and keyway")
bore.addProperty("App::PropertyString", "KeywayLocation", "Bore and keyway")
bore.KeywayLocation = "Centered on +Y; through all"
bore_tool = Part.makeCylinder(bore.BoreDiameter.Value / 2.0, face_width + 0.02,
                              App.Vector(0, 0, -0.01))
# Rectangle runs from the axis to its floor at Y=10.3; its overlap with the
# circular bore gives the conventional open-ended keyway.
key_tool = Part.makeBox(bore.KeywayWidth.Value, bore.KeywayFloorRadius.Value,
                        face_width + 0.02,
                        App.Vector(-bore.KeywayWidth.Value / 2.0, 0, -0.01))
final_shape = holes.Shape.cut(bore_tool.fuse(key_tool)).removeSplitter()
bore.Shape = final_shape
bore.addProperty("App::PropertyString", "Result", "Validation")
bore.Result = "Single solid finished gear"

for obj in (blank, top_recess, bottom_recess, holes):
    obj.Visibility = False
bore.Label = "05 Finished gear: bore and keyway"

doc.recompute()
if len(final_shape.Solids) != 1:
    raise RuntimeError("Gear construction did not produce exactly one solid")
doc.recompute()
doc.saveAs(OUT_FILE)
print("Saved", OUT_FILE)
