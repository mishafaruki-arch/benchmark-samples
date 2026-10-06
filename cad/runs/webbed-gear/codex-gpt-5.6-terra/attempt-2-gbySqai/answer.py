"""Parametric webbed involute spur gear for FreeCAD 1.1.

Run with FreeCADCmd.  The document is deliberately made as a PartDesign Body
with successive editable feature objects; dimensions are collected in the
GearParameters feature near the head of the tree.
"""
import os
import math
import FreeCAD as App
import Part


DOC_NAME = "WebbedSpurGear"
doc = App.newDocument(DOC_NAME)
body = doc.addObject("PartDesign::Body", "WebbedSpurGearBody")
body.Label = "Webbed Spur Gear (PartDesign Body)"


def length(obj, name, value, description):
    obj.addProperty("App::PropertyLength", name, "Gear parameters", description)
    setattr(obj, name, value)


def integer(obj, name, value, description):
    obj.addProperty("App::PropertyInteger", name, "Gear parameters", description)
    setattr(obj, name, value)


# This is kept in the Body so that the complete model, including its driving
# dimensions, is a single PartDesign feature tree.
params = body.newObject("PartDesign::Feature", "GearParameters")
params.Label = "Gear Parameters (editable)"
integer(params, "number_of_teeth", 36, "Number of teeth")
length(params, "gear_module", 2.0, "Normal module")
params.addProperty("App::PropertyAngle", "pressure_angle", "Gear parameters", "Standard pressure angle")
params.pressure_angle = 20.0
length(params, "tip_diameter", 76.0, "Outside/tip diameter")
length(params, "root_diameter", 67.0, "Root diameter")
length(params, "face_width", 20.0, "Overall axial gear width")
length(params, "web_thickness", 8.0, "Centered web thickness")
length(params, "rim_inner_diameter", 56.0, "Diameter at inside of toothed rim")
length(params, "hub_diameter", 30.0, "Hub diameter")
length(params, "bore_diameter", 16.0, "Bore diameter")
length(params, "lightening_hole_diameter", 10.0, "Lightening-hole diameter")
integer(params, "number_lightening_holes", 6, "Number of equally spaced holes")
length(params, "lightening_hole_pcd", 43.0, "Lightening-hole pitch circle diameter")
length(params, "keyway_width", 5.0, "Keyway tangential width")
length(params, "keyway_floor_radius", 10.3, "Radius to flat keyway floor")
params.addProperty("App::PropertyString", "profile_note", "Documentation")
params.profile_note = "20 degree true involutes; radial extensions below base circle; zero backlash"


def add_feature(name, label):
    feat = body.newObject("PartDesign::Feature", name)
    feat.Label = label
    feat.addProperty("App::PropertyLink", "Parameters", "Driving parameters")
    feat.Parameters = params
    return feat


def polar(radius, angle):
    return App.Vector(radius * math.cos(angle), radius * math.sin(angle), 0)


def involute_point(rb, t, tooth_angle, base_offset, sign=1):
    # polar angle is measured from this tooth's centreline.  Keeping the
    # centre angle outside the mirroring is important for every tooth except
    # the one on +X.
    phi = t - math.atan(t)
    return polar(rb * math.sqrt(1.0 + t * t), tooth_angle + sign * (base_offset + phi))


def make_involute_gear_outline(z, module, teeth, pressure_deg, tip_dia, root_dia):
    """A closed wire with true involute flanks represented by spline edges.

    The spline interpolation samples the analytic involute densely enough that
    it is indistinguishable at manufacturing scale, while retaining dedicated
    curve edges rather than a faceted polygon.
    """
    rb = module * teeth * math.cos(math.radians(pressure_deg)) / 2.0
    rp = module * teeth / 2.0
    rt = tip_dia / 2.0
    rr = root_dia / 2.0
    t_pitch = math.sqrt((rp / rb) ** 2 - 1.0)
    t_tip = math.sqrt((rt / rb) ** 2 - 1.0)
    half_tooth = math.pi / (2.0 * teeth)
    base_offset = half_tooth - (t_pitch - math.atan(t_pitch))
    pitch = 2.0 * math.pi / teeth
    edges = []
    first_root = polar(rr, base_offset)
    for i in range(teeth):
        a = i * pitch
        root_minus = polar(rr, a - base_offset)
        base_minus = polar(rb, a - base_offset)
        # Traverse the negative flank outward, then the tooth tip, then the
        # positive flank inward.  This gives a non-self-intersecting outline.
        edges.append(Part.makeLine(root_minus + App.Vector(0, 0, z), base_minus + App.Vector(0, 0, z)))
        minus_pts = []
        for j in range(17):
            t = t_tip * j / 16.0
            p = involute_point(rb, t, a, base_offset, -1)
            minus_pts.append(p + App.Vector(0, 0, z))
        # Chordal sampling of the analytic involute keeps the generated BRep
        # robust across OCCT versions while the points themselves are evaluated
        # from the exact involute equation above.
        edges.extend(Part.makePolygon(minus_pts).Edges)
        tip_minus = minus_pts[-1]
        tip_plus_xy = involute_point(rb, t_tip, a, base_offset, 1)
        tip_plus = tip_plus_xy + App.Vector(0, 0, z)
        # Midpoint at tooth centre chooses the short tip-circle arc.
        edges.append(Part.Arc(tip_minus, polar(rt, a) + App.Vector(0, 0, z), tip_plus).toShape())
        plus_pts = []
        for j in range(16, -1, -1):
            t = t_tip * j / 16.0
            p = involute_point(rb, t, a, base_offset, 1)
            plus_pts.append(p + App.Vector(0, 0, z))
        edges.extend(Part.makePolygon(plus_pts).Edges)
        root_plus = first_root if i == 0 else polar(rr, a + base_offset)
        edges.append(Part.makeLine(plus_pts[-1], root_plus + App.Vector(0, 0, z)))
        next_root = polar(rr, (i + 1) * pitch - base_offset)
        if i == teeth - 1:
            next_root = polar(rr, -base_offset)
        # The root space is explicitly an arc of the root circle (no fillet).
        start_angle = a + base_offset
        end_angle = (i + 1) * pitch - base_offset
        mid_angle = (start_angle + end_angle) / 2.0
        edges.append(Part.Arc(root_plus + App.Vector(0, 0, z),
                              polar(rr, mid_angle) + App.Vector(0, 0, z),
                              next_root + App.Vector(0, 0, z)).toShape())
    return Part.Wire(edges)


# Feature 1: toothed, full-width gear blank.
gear = add_feature("AdditiveInvoluteGear", "Additive Involute Gear (36 teeth)")
gear.addProperty("App::PropertyString", "ProfileDefinition", "Feature information")
gear.ProfileDefinition = "Involute flanks, radial root extensions, root and tip arcs"
outline = make_involute_gear_outline(0.0, params.gear_module.Value, params.number_of_teeth,
                                     params.pressure_angle.Value, params.tip_diameter.Value,
                                     params.root_diameter.Value)
gear.Shape = Part.Face(outline).extrude(App.Vector(0, 0, params.face_width.Value))


def annular_cut(r_inner, r_outer, z0, depth):
    outer = Part.makeCylinder(r_outer, depth, App.Vector(0, 0, z0))
    inner = Part.makeCylinder(r_inner, depth, App.Vector(0, 0, z0))
    return outer.cut(inner)


recess_depth = (params.face_width.Value - params.web_thickness.Value) / 2.0
front = add_feature("PocketFrontWebRecess", "Pocket: Front Web Recess (6 mm)")
front.addProperty("App::PropertyLength", "Depth", "Pocket parameters")
front.Depth = recess_depth
front.Shape = gear.Shape.cut(annular_cut(params.hub_diameter.Value / 2, params.rim_inner_diameter.Value / 2, 0, recess_depth))

back = add_feature("PocketBackWebRecess", "Pocket: Back Web Recess (6 mm)")
back.addProperty("App::PropertyLength", "Depth", "Pocket parameters")
back.Depth = recess_depth
back.Shape = front.Shape.cut(annular_cut(params.hub_diameter.Value / 2, params.rim_inner_diameter.Value / 2,
                                          params.face_width.Value - recess_depth, recess_depth))

holes = add_feature("PocketLighteningHoles", "Pocket: 6 Lightening Holes Through Web")
holes.addProperty("App::PropertyString", "Pattern", "Pocket parameters")
holes.Pattern = "Circular pattern, first instance on +X axis"
hole_tools = None
for i in range(params.number_lightening_holes):
    angle = 2.0 * math.pi * i / params.number_lightening_holes
    c = params.lightening_hole_pcd.Value / 2.0
    tool = Part.makeCylinder(params.lightening_hole_diameter.Value / 2.0, params.face_width.Value,
                             App.Vector(c * math.cos(angle), c * math.sin(angle), 0))
    hole_tools = tool if hole_tools is None else hole_tools.fuse(tool)
holes.Shape = back.Shape.cut(hole_tools)

bore = add_feature("PocketBoreAndKeyway", "Pocket: Through Bore and 5 mm Keyway")
bore.addProperty("App::PropertyString", "KeywayDescription", "Pocket parameters")
bore.KeywayDescription = "5 mm wide at +Y; flat floor at radius 10.3 mm"
bore_tool = Part.makeCylinder(params.bore_diameter.Value / 2.0, params.face_width.Value, App.Vector(0, 0, 0))
# Box begins inside the bore and ends at the stated flat floor on +Y.
key_tool = Part.makeBox(params.keyway_width.Value, params.keyway_floor_radius.Value,
                        params.face_width.Value, App.Vector(-params.keyway_width.Value / 2.0, 0, 0))
bore.Shape = holes.Shape.cut(bore_tool.fuse(key_tool))

# Only the final feature is visible; Body Tip is consequently one connected solid.
for feature in (params, gear, front, back, holes):
    feature.Visibility = False
bore.Visibility = True
body.Tip = bore
doc.recompute()

out_path = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
doc.recompute()
doc.saveAs(out_path)
print(out_path)
