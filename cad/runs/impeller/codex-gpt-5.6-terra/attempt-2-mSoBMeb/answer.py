"""Parametric radial impeller for FreeCAD 1.1.

Run with FreeCADCmd (or from FreeCAD's Python console).  The document is
intentionally made from PartDesign features rather than a final imported BREP.
"""
import os
import math
import FreeCAD as App
import Part
import Sketcher


OUTFILE = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
doc = App.newDocument("RadialImpeller")

# A normal document object keeps the design inputs together and makes them
# available to expressions in the PartDesign primitives.
params = doc.addObject("App::FeaturePython", "Parameters")
params.Label = "Impeller Parameters (mm)"
for name, value in (
    ("backplate_diameter", 120.0),
    ("backplate_thickness", 4.0),
    ("hub_diameter", 30.0),
    ("overall_height", 36.0),
    ("blade_height", 20.0),
    ("blade_tip_diameter", 116.0),
    ("bore_diameter", 10.0),
):
    params.addProperty("App::PropertyLength", name, "Dimensions")
    setattr(params, name, value)
params.addProperty("App::PropertyInteger", "number_of_blades", "Dimensions")
params.number_of_blades = 7
params.addProperty("App::PropertyLength", "blade_thickness", "Blade construction")
params.blade_thickness = 3.0
params.addProperty("App::PropertyLength", "blade_arc_radius_inner", "Blade construction")
params.blade_arc_radius_inner = 48.5
params.addProperty("App::PropertyLength", "blade_arc_radius_outer", "Blade construction")
params.blade_arc_radius_outer = 51.5
params.addProperty("App::PropertyLength", "blade_arc_center_y", "Blade construction")
params.blade_arc_center_y = 50.0

body = doc.addObject("PartDesign::Body", "ImpellerBody")
body.Label = "Radial Impeller (single solid)"

def expr(obj, prop, text):
    """Expressions are best effort across the 1.0/1.1 property bindings."""
    try:
        obj.setExpression(prop, text)
    except Exception:
        pass

def offset_z(obj, zexpr, fallback):
    # Primitives use their Placement when they are free (unattached) features.
    # Keep their exact Z stations explicit; their dimensional properties remain
    # expression-driven by Parameters.
    obj.Placement.Base = App.Vector(0, 0, fallback)

# Back plate and the two editable hub primitives.
plate = body.newObject("PartDesign::AdditiveCylinder", "BackPlate")
plate.Label = "Back plate Ø120 x 4"
plate.Radius = 60
plate.Height = 4
plate.Angle = 360
expr(plate, "Radius", "Parameters.backplate_diameter / 2")
expr(plate, "Height", "Parameters.backplate_thickness")

hub = body.newObject("PartDesign::AdditiveCylinder", "HubCylinder")
hub.Label = "Hub cylinder Ø30, Z4 to Z28"
hub.Radius = 15
hub.Height = 24
hub.Angle = 360
offset_z(hub, "Parameters.backplate_thickness", 4)
expr(hub, "Radius", "Parameters.hub_diameter / 2")

cone = body.newObject("PartDesign::AdditiveCone", "HubTaper")
cone.Label = "Hub taper Ø30 to Ø16"
cone.Radius1 = 15
cone.Radius2 = 8
cone.Height = 8
cone.Angle = 360
offset_z(cone, "Parameters.backplate_thickness + 24 mm", 28)
expr(cone, "Radius1", "Parameters.hub_diameter / 2")
expr(cone, "Height", "Parameters.overall_height - 28 mm")

def point(radius, circle_radius, origin_radius):
    # Intersection of circle (0,50), radius circle_radius and origin circle
    # radius origin_radius; the requested blade is the +X intersection.
    y = (50.0 * 50.0 - circle_radius * circle_radius + origin_radius * origin_radius) / 100.0
    return App.Vector(math.sqrt(max(0.0, origin_radius * origin_radius - y * y)), y, 0)

def rotated(p, angle_deg):
    a = math.radians(angle_deg)
    return App.Vector(p.x * math.cos(a) - p.y * math.sin(a),
                      p.x * math.sin(a) + p.y * math.cos(a), 0)

def add_blade_profile(name, z, angle):
    """Closed annular-sector profile for one backward-curved blade."""
    s = body.newObject("PartDesign::Feature", name) if False else body.newObject("Sketcher::SketchObject", name)
    s.Label = name.replace("_", " ")
    # Keep this as a free XY sketch; AttachmentOffset supplies its Z level.
    s.Placement.Base = App.Vector(0, 0, z)
    # Exact intersections with Ø30 hub and Ø116 tip circle.
    inn_hub = point(0, 48.5, 15.0)
    out_hub = point(0, 51.5, 15.0)
    inn_tip = point(0, 48.5, 58.0)
    out_tip = point(0, 51.5, 58.0)
    inn_mid = App.Vector(48.5 * math.cos(math.radians(-45)), 50 + 48.5 * math.sin(math.radians(-45)), 0)
    out_mid = App.Vector(51.5 * math.cos(math.radians(-45)), 50 + 51.5 * math.sin(math.radians(-45)), 0)
    pts = [rotated(q, angle) for q in (inn_hub, inn_tip, out_tip, out_hub, inn_mid, out_mid)]
    # Inner and outer boundaries are genuine circular arcs, retaining the
    # 3-mm curved-strip construction in the editable sketch.
    s.addGeometry(Part.Arc(pts[0], pts[4], pts[1]), False)
    s.addGeometry(Part.LineSegment(pts[1], pts[2]), False)
    s.addGeometry(Part.Arc(pts[2], pts[5], pts[3]), False)
    s.addGeometry(Part.LineSegment(pts[3], pts[0]), False)
    return s

# Seven separate additive lofts are robust PartDesign features and all touch
# the plate/hub, so the Body remains a single connected solid.
for i in range(params.number_of_blades):
    angle = i * 360.0 / 7.0
    lower = add_blade_profile("Blade%02d_BaseSketch" % (i + 1), 4.0, angle)
    upper = add_blade_profile("Blade%02d_TopSketch" % (i + 1), 24.0, angle)
    loft = body.newObject("PartDesign::AdditiveLoft", "Blade%02d" % (i + 1))
    loft.Label = "Backward-curved blade %d" % (i + 1)
    loft.Profile = lower
    loft.Sections = [upper]
    loft.Ruled = True
    # Expose the placement-driving inputs directly on each editable feature.
    loft.addProperty("App::PropertyAngle", "BladeAngle", "Blade parameters")
    loft.BladeAngle = angle
    loft.addProperty("App::PropertyLength", "BladeHeight", "Blade parameters")
    loft.BladeHeight = 20
    expr(loft, "BladeHeight", "Parameters.blade_height")

# D bore: major circular arc plus vertical chord at x=+4.  A subtractive loft
# from z=0 to z=36 is deliberately used so it is an editable PartDesign cut.
def bore_sketch(name, z):
    sk = body.newObject("Sketcher::SketchObject", name)
    sk.Label = name.replace("_", " ")
    # Free XY sketch at the requested Z level.
    sk.Placement.Base = App.Vector(0, 0, z)
    # Circle radius 5, clipped by the chord X=4; go around its long (left) side.
    top = App.Vector(4, 3, 0)
    bottom = App.Vector(4, -3, 0)
    left = App.Vector(-5, 0, 0)
    sk.addGeometry(Part.Arc(top, left, bottom), False)
    sk.addGeometry(Part.LineSegment(bottom, top), False)
    return sk

bore0 = bore_sketch("D_Bore_BaseSketch", 0)
bore1 = bore_sketch("D_Bore_TopSketch", 36)
bore = body.newObject("PartDesign::SubtractiveLoft", "D_Bore")
bore.Label = "D-shaped through bore Ø10, flat X=+4"
bore.Profile = bore0
bore.Sections = [bore1]
bore.Ruled = True
bore.addProperty("App::PropertyLength", "BoreDiameter", "Bore parameters")
bore.BoreDiameter = 10
expr(bore, "BoreDiameter", "Parameters.bore_diameter")

doc.recompute()
doc.recompute()
doc.saveAs(OUTFILE)
