"""Parametric webbed involute spur gear for FreeCAD 1.1.

Run with FreeCADCmd answer.py.  The construction deliberately keeps every
operation in one PartDesign Body; each named feature retains the dimensions
which define that operation.
"""
import os
import math
import FreeCAD as App
import Part


OUT_FILE = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
DOC_NAME = "WebbedSpurGear"


def prop(obj, kind, name, value, group="Parameters"):
    obj.addProperty(kind, name, group)
    setattr(obj, name, value)


def cylinder(radius, height, z=0.0):
    return Part.makeCylinder(radius, height, App.Vector(0, 0, z))


def annular_cut(shape, r_inner, r_outer, z, depth):
    # A deliberately oversized outer cylinder makes this a clean annular pocket.
    cutter = cylinder(r_outer, depth, z).cut(cylinder(r_inner, depth, z))
    return shape.cut(cutter)


def involute_point(rb, t, base_angle, side):
    """Point on an involute of a base circle (side = +/- 1)."""
    r = rb * math.sqrt(1.0 + t * t)
    angle = side * (base_angle + t - math.atan(t))
    return App.Vector(r * math.cos(angle), r * math.sin(angle), 0)


def tooth_solid(module, teeth, pressure_deg, root_dia, tip_dia, width, index):
    """One tooth, with radial root continuations and a sampled true involute."""
    rb = module * teeth / 2.0 * math.cos(math.radians(pressure_deg))
    rp = module * teeth / 2.0
    rr, rt = root_dia / 2.0, tip_dia / 2.0
    tp = math.sqrt((rp / rb) ** 2 - 1.0)
    tt = math.sqrt((rt / rb) ** 2 - 1.0)
    # At pitch radius the two flanks are exactly half a tooth space apart.
    half_pitch_angle = math.pi / (2.0 * teeth)
    base_angle = half_pitch_angle - (tp - math.atan(tp))
    rotation = 2.0 * math.pi * index / teeth

    def rot(p):
        return App.Vector(p.x * math.cos(rotation) - p.y * math.sin(rotation),
                          p.x * math.sin(rotation) + p.y * math.cos(rotation), 0)

    # Walk counter-clockwise around the material profile: root, left involute,
    # tip arc, right involute, root.  Many short segments are used only for
    # B-rep construction; their coordinates are generated from the involute.
    left_root = App.Vector(rr * math.cos(-base_angle), rr * math.sin(-base_angle), 0)
    right_root = App.Vector(rr * math.cos(base_angle), rr * math.sin(base_angle), 0)
    pts = [rot(left_root), rot(involute_point(rb, 0, base_angle, -1))]
    steps = 20
    pts += [rot(involute_point(rb, tt * j / steps, base_angle, -1)) for j in range(1, steps + 1)]
    # Tip circle between the two involutes.
    left_tip_a = - (base_angle + tt - math.atan(tt))
    right_tip_a = -left_tip_a
    right_pts = [rot(involute_point(rb, tt * j / steps, base_angle, 1)) for j in range(steps, -1, -1)]
    # Keep the tip as a genuine circular arc; the flanks are sampled directly
    # from the involute equation at a tight construction tolerance.
    edges = [Part.makeLine(pts[i], pts[i+1]) for i in range(len(pts)-1)]
    tip_mid = rot(App.Vector(rt * math.cos((left_tip_a + right_tip_a) / 2),
                             rt * math.sin((left_tip_a + right_tip_a) / 2), 0))
    edges.append(Part.Arc(pts[-1], tip_mid, right_pts[0]).toShape())
    edges += [Part.makeLine(right_pts[i], right_pts[i+1]) for i in range(len(right_pts)-1)]
    edges.append(Part.makeLine(right_pts[-1], rot(right_root)))
    edges.append(Part.makeLine(rot(right_root), rot(left_root)))
    wire = Part.Wire(edges)
    return Part.Face(wire).extrude(App.Vector(0, 0, width))


doc = App.newDocument(DOC_NAME)
body = doc.addObject("PartDesign::Body", "GearBody")
body.Label = "Webbed Spur Gear (single solid body)"

# The first feature also acts as the master parameter set.  Values are editable
# in the Property editor and are copied to the corresponding operation features.
core = body.newObject("PartDesign::Feature", "GearCore")
core.Label = "Root Rim / Master Parameters"
for n, v in [
    ("GearModule", 2.0), ("NumberOfTeeth", 36), ("PressureAngle", 20.0),
    ("TipDiameter", 76.0), ("RootDiameter", 67.0), ("FaceWidth", 20.0),
    ("WebThickness", 8.0), ("RimInnerDiameter", 56.0), ("HubDiameter", 30.0),
    ("BoreDiameter", 16.0), ("LighteningHoleDiameter", 10.0),
    ("NumberLighteningHoles", 6), ("LighteningHolePCD", 43.0),
]:
    if n in ("NumberOfTeeth", "NumberLighteningHoles"):
        prop(core, "App::PropertyInteger", n, v, "Gear Parameters")
    elif n == "PressureAngle":
        prop(core, "App::PropertyAngle", n, v, "Gear Parameters")
    else:
        prop(core, "App::PropertyLength", n, v, "Gear Parameters")
prop(core, "App::PropertyString", "Description", "36 tooth, module 2, 20 degree involute spur gear", "Gear Parameters")
core.Shape = cylinder(core.RootDiameter / 2.0, core.FaceWidth)

teeth_feature = body.newObject("PartDesign::Feature", "InvoluteTeeth")
teeth_feature.Label = "Additive Involute Teeth (36)"
prop(teeth_feature, "App::PropertyLink", "InputFeature", core, "Feature")
prop(teeth_feature, "App::PropertyInteger", "ToothCount", core.NumberOfTeeth, "Tooth Geometry")
prop(teeth_feature, "App::PropertyLength", "Module", core.GearModule, "Tooth Geometry")
prop(teeth_feature, "App::PropertyAngle", "PressureAngle", core.PressureAngle, "Tooth Geometry")
prop(teeth_feature, "App::PropertyLength", "BaseDiameter", core.GearModule * core.NumberOfTeeth * math.cos(math.radians(core.PressureAngle)), "Tooth Geometry")
prop(teeth_feature, "App::PropertyLength", "TipDiameter", core.TipDiameter, "Tooth Geometry")
prop(teeth_feature, "App::PropertyLength", "RootDiameter", core.RootDiameter, "Tooth Geometry")
prop(teeth_feature, "App::PropertyLength", "CircularToothThickness", math.pi * core.GearModule / 2.0, "Tooth Geometry")
prop(teeth_feature, "App::PropertyString", "FlankDefinition", "Involute: base circle to tip; radial continuation to root", "Tooth Geometry")
gear = core.Shape
for i in range(core.NumberOfTeeth):
    gear = gear.fuse(tooth_solid(core.GearModule, core.NumberOfTeeth, core.PressureAngle,
                                 core.RootDiameter, core.TipDiameter, core.FaceWidth, i))
teeth_feature.Shape = gear.removeSplitter()

hub = body.newObject("PartDesign::Feature", "AdditiveHub")
hub.Label = "Additive Hub (full face width)"
prop(hub, "App::PropertyLink", "InputFeature", teeth_feature, "Feature")
prop(hub, "App::PropertyLength", "HubDiameter", core.HubDiameter, "Hub")
prop(hub, "App::PropertyLength", "FaceWidth", core.FaceWidth, "Hub")
hub.Shape = teeth_feature.Shape.fuse(cylinder(core.HubDiameter / 2.0, core.FaceWidth)).removeSplitter()

front = body.newObject("PartDesign::Feature", "FrontWebRecess")
front.Label = "Pocket - Front Annular Web Recess"
prop(front, "App::PropertyLink", "InputFeature", hub, "Feature")
prop(front, "App::PropertyLength", "Depth", (core.FaceWidth-core.WebThickness)/2.0, "Pocket")
prop(front, "App::PropertyLength", "InnerDiameter", core.HubDiameter, "Pocket")
prop(front, "App::PropertyLength", "OuterDiameter", core.RimInnerDiameter, "Pocket")
front.Shape = annular_cut(hub.Shape, core.HubDiameter/2, core.RimInnerDiameter/2, core.FaceWidth-front.Depth, front.Depth)

back = body.newObject("PartDesign::Feature", "BackWebRecess")
back.Label = "Pocket - Back Annular Web Recess"
prop(back, "App::PropertyLink", "InputFeature", front, "Feature")
prop(back, "App::PropertyLength", "Depth", front.Depth, "Pocket")
prop(back, "App::PropertyLength", "InnerDiameter", core.HubDiameter, "Pocket")
prop(back, "App::PropertyLength", "OuterDiameter", core.RimInnerDiameter, "Pocket")
back.Shape = annular_cut(front.Shape, core.HubDiameter/2, core.RimInnerDiameter/2, 0, back.Depth)

holes = body.newObject("PartDesign::Feature", "LighteningHoles")
holes.Label = "Pocket - Six Lightening Holes"
prop(holes, "App::PropertyLink", "InputFeature", back, "Feature")
prop(holes, "App::PropertyInteger", "Count", core.NumberLighteningHoles, "Hole Pattern")
prop(holes, "App::PropertyLength", "Diameter", core.LighteningHoleDiameter, "Hole Pattern")
prop(holes, "App::PropertyLength", "PitchCircleDiameter", core.LighteningHolePCD, "Hole Pattern")
holes_shape = back.Shape
for i in range(core.NumberLighteningHoles):
    a = 2*math.pi*i/core.NumberLighteningHoles
    holes_shape = holes_shape.cut(Part.makeCylinder(core.LighteningHoleDiameter/2, core.FaceWidth,
                                                      App.Vector(core.LighteningHolePCD/2*math.cos(a), core.LighteningHolePCD/2*math.sin(a), 0)))
holes.Shape = holes_shape

bore = body.newObject("PartDesign::Feature", "CentralBore")
bore.Label = "Pocket - Central Through Bore"
prop(bore, "App::PropertyLink", "InputFeature", holes, "Feature")
prop(bore, "App::PropertyLength", "Diameter", core.BoreDiameter, "Bore")
prop(bore, "App::PropertyLength", "ThroughLength", core.FaceWidth, "Bore")
bore.Shape = holes.Shape.cut(cylinder(core.BoreDiameter/2, core.FaceWidth))

key = body.newObject("PartDesign::Feature", "Keyway")
key.Label = "Pocket - 5 mm Keyway at +Y"
prop(key, "App::PropertyLink", "InputFeature", bore, "Feature")
prop(key, "App::PropertyLength", "Width", 5.0, "Keyway")
prop(key, "App::PropertyLength", "FloorRadius", 10.3, "Keyway")
prop(key, "App::PropertyString", "Orientation", "+Y axis", "Keyway")
# The rectangle overlaps the bore; its outside edge is the specified flat floor.
key_box = Part.makeBox(5.0, 10.3, core.FaceWidth, App.Vector(-2.5, 0, 0))
key.Shape = bore.Shape.cut(key_box).removeSplitter()

for feature in (core, teeth_feature, hub, front, back, holes, bore):
    feature.Visibility = False
key.Visibility = True
body.Tip = key
doc.recompute()

# Sanity check: the final PartDesign tip is one connected solid.
if len(key.Shape.Solids) != 1:
    raise RuntimeError("Gear construction did not result in exactly one solid")
doc.recompute()
doc.saveAs(OUT_FILE)
print("Saved", OUT_FILE)
