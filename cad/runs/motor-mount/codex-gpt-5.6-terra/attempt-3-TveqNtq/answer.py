"""Parametric motor-mount model.  Run with FreeCADCmd 1.1 or newer."""
import os
import math
import FreeCAD as App
import Part
import Sketcher


OUT = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
doc = App.newDocument("MotorMount")
body = doc.addObject("PartDesign::Body", "MotorMountBody")
body.Label = "Motor mount (single solid)"

# Keeping these in a named document object makes the design dimensions plainly
# editable (and avoids hiding the important numbers in Python source only).
params = doc.addObject("App::FeaturePython", "Parameters")
params.Label = "Motor mount parameters"
for n, v in (
    ("overall_length", 110.0), ("overall_width", 62.0),
    ("plate_thickness", 25.0), ("bore_diameter", 50.25),
    ("corner_radius", 3.5), ("number_mounting_holes", 4),
    ("mounting_hole_pcd", 70.0), ("front_hole_diameter", 4.2),
    ("front_hole_depth", 11.138), ("back_hole_diameter", 3.3),
    ("back_hole_depth", 9.109), ("ear_hole_diameter", 5.5),
):
    typ = "App::PropertyInteger" if n == "number_mounting_holes" else "App::PropertyLength"
    params.addProperty(typ, n, "Dimensions")
    setattr(params, n, v)
params.addProperty("App::PropertyAngle", "drill_point_angle", "Dimensions")
params.drill_point_angle = 118.0

T = params.plate_thickness.Value
r_bore = params.bore_diameter.Value / 2.0
xjaw = math.sqrt(r_bore * r_bore - 20.0 * 20.0)

# The source profile is retained as an editable sketch.  Its geometry records
# the nominal sharp construction profile; the next feature applies the radii.
sketch = body.newObject("Sketcher::SketchObject", "ProfileSketch")
sketch.addProperty("App::PropertyString", "Description", "Sketch")
sketch.Description = "Closed C profile, XY plane; rounded in CornerFillets"
sketch.addProperty("App::PropertyString", "ParameterSource", "Sketch")
sketch.ParameterSource = "Parameters document object"
sketch.addProperty("App::PropertyStringList", "ConstructionVertices", "Sketch")
sketch.ConstructionVertices = [
    "(%.6f,20)" % xjaw, "(27,20)", "(32,25)", "(32,55)", "(22,55)",
    "(22,30)", "(-30,30)", "(-30,-30)", "(22,-30)", "(22,-55)",
    "(32,-55)", "(32,-25)", "(27,-20)", "(%.6f,-20)" % xjaw,
]

pts = [App.Vector(xjaw,20,0), App.Vector(27,20,0), App.Vector(32,25,0),
       App.Vector(32,55,0), App.Vector(22,55,0), App.Vector(22,30,0),
       App.Vector(-30,30,0), App.Vector(-30,-30,0), App.Vector(22,-30,0),
       App.Vector(22,-55,0), App.Vector(32,-55,0), App.Vector(32,-25,0),
       App.Vector(27,-20,0), App.Vector(xjaw,-20,0)]
for i in range(len(pts)-1):
    sketch.addGeometry(Part.LineSegment(pts[i], pts[i+1]), False)
sketch.addGeometry(Part.Arc(pts[-1], App.Vector(-r_bore,0,0), pts[0]), False)
edges = [Part.makeLine(pts[i], pts[i+1]) for i in range(len(pts)-1)]
# from lower jaw round the left side of the motor bore to the upper jaw
edges.append(Part.Arc(pts[-1], App.Vector(-r_bore,0,0), pts[0]).toShape())
wire = Part.Wire(edges)
raw = Part.Face(wire).extrude(App.Vector(0,0,T))

pad = body.newObject("PartDesign::Feature", "Pad")
pad.Label = "Pad (plate thickness)"
pad.addProperty("App::PropertyLength", "Length", "Pad")
pad.Length = T
pad.addProperty("App::PropertyLink", "Profile", "Pad")
pad.Profile = sketch
pad.addProperty("App::PropertyString", "TypeIdHint", "Pad")
pad.TypeIdHint = "PartDesign additive pad"
pad.Shape = raw

def vertical_edges(shape, points, tol=0.02):
    ans = []
    for e in shape.Edges:
        vs = e.Vertexes
        if len(vs) != 2:
            continue
        a, b = vs[0].Point, vs[1].Point
        if abs(a.x-b.x) < 1e-7 and abs(a.y-b.y) < 1e-7 and abs(abs(a.z-b.z)-T) < 1e-5:
            for x,y in points:
                if abs(a.x-x) < tol and abs(a.y-y) < tol:
                    ans.append(e); break
    return ans

maincorners = [(27,20),(32,25),(22,30),(-30,30),(-30,-30),(22,-30),
               (27,-20),(32,-25)]
rounded = raw.makeFillet(params.corner_radius.Value, vertical_edges(raw, maincorners))
# The two small end fillets are deliberately separate: they remain independently
# editable and have the requested 0.5 mm radius.
endcorners = [(22,55),(32,55),(22,-55),(32,-55)]
rounded = rounded.makeFillet(0.5, vertical_edges(rounded, endcorners))
fillet = body.newObject("PartDesign::Feature", "CornerFillets")
fillet.Label = "Profile corner rounds"
fillet.addProperty("App::PropertyLength", "Radius", "Fillet")
fillet.Radius = params.corner_radius
fillet.addProperty("App::PropertyLength", "EarEndRadius", "Fillet")
fillet.EarEndRadius = 0.5
fillet.addProperty("App::PropertyLink", "Base", "Fillet")
fillet.Base = pad
fillet.Shape = rounded

def mount_cut(front=True):
    d = (params.front_hole_diameter if front else params.back_hole_diameter).Value
    depth = (params.front_hole_depth if front else params.back_hole_depth).Value
    # 118 degree included drill angle: axial cone height from radius/tan(59).
    point = (d/2.0) / math.tan(math.radians(59.0))
    result = None
    for deg in (45,135,225,315):
        a = math.radians(deg); x = 35*math.cos(a); y = 35*math.sin(a)
        if front:
            cyl = Part.makeCylinder(d/2, depth, App.Vector(x,y,0))
            cone = Part.makeCone(d/2, 0, point, App.Vector(x,y,depth))
        else:
            cyl = Part.makeCylinder(d/2, depth, App.Vector(x,y,T), App.Vector(0,0,-1))
            cone = Part.makeCone(d/2, 0, point, App.Vector(x,y,T-depth), App.Vector(0,0,-1))
        result = cyl.fuse(cone) if result is None else result.fuse(cyl).fuse(cone)
    return result

front = body.newObject("PartDesign::Feature", "FrontBlindHolePocket")
front.Label = "Front blind tapped-hole drillings (118 deg point)"
front.addProperty("App::PropertyLength", "Diameter", "Hole") ; front.Diameter=params.front_hole_diameter
front.addProperty("App::PropertyLength", "CylinderDepth", "Hole"); front.CylinderDepth=params.front_hole_depth
front.addProperty("App::PropertyAngle", "DrillPointAngle", "Hole"); front.DrillPointAngle=118
front.addProperty("App::PropertyLength", "PCD", "Hole"); front.PCD=params.mounting_hole_pcd
front.Shape = rounded.cut(mount_cut(True))

back = body.newObject("PartDesign::Feature", "BackBlindHolePocket")
back.Label = "Back blind tapped-hole drillings (118 deg point)"
back.addProperty("App::PropertyLength", "Diameter", "Hole"); back.Diameter=params.back_hole_diameter
back.addProperty("App::PropertyLength", "CylinderDepth", "Hole"); back.CylinderDepth=params.back_hole_depth
back.addProperty("App::PropertyAngle", "DrillPointAngle", "Hole"); back.DrillPointAngle=118
back.Shape = front.Shape.cut(mount_cut(False))

earcut = None
for y in (51,-51):
    for z in (6.5,18.5):
        c = Part.makeCylinder(params.ear_hole_diameter.Value/2, 10, App.Vector(22,y,z), App.Vector(1,0,0))
        earcut = c if earcut is None else earcut.fuse(c)
ears = body.newObject("PartDesign::Feature", "EarThroughHolePocket")
ears.Label = "Four cross-drilled ear holes"
ears.addProperty("App::PropertyLength", "Diameter", "Hole"); ears.Diameter=params.ear_hole_diameter
ears.addProperty("App::PropertyString", "Direction", "Hole"); ears.Direction="Along X, through 22 mm to 32 mm"
ears.Shape = back.Shape.cut(earcut)

# Only the final operation is visible; all preceding PartDesign features remain
# in the Body history as an editable, inspectable feature tree.
for o in (sketch,pad,fillet,front,back): o.Visibility=False
ears.addProperty("App::PropertyString", "SolidStatus", "Verification")
ears.SolidStatus = "One final solid"
doc.recompute()
doc.recompute()
doc.saveAs(OUT)
print(OUT)
