"""Parametric PartDesign model of a splined stepped drive shaft.

Run with FreeCAD's Python interpreter.  The file is deliberately self-contained:
all dimensions are editable properties on the PartDesign features in the Body.
"""
import os
import FreeCAD as App
import Part


V = App.Vector


def add_length(obj, name, value, description=""):
    obj.addProperty("App::PropertyLength", name, "Parameters", description)
    setattr(obj, name, value)


def add_integer(obj, name, value, description=""):
    obj.addProperty("App::PropertyInteger", name, "Parameters", description)
    setattr(obj, name, value)


class BaseProfileProxy:
    """Revolved, chamfered, stepped blank."""
    def execute(self, obj):
        z = float(obj.OverallLength)
        r0 = float(obj.SplineMajorDiameter) / 2.0
        rb = float(obj.BearingDiameter) / 2.0
        rc = float(obj.CollarDiameter) / 2.0
        re = float(obj.EndDiameter) / 2.0
        c = float(obj.EndChamfer)
        # Closed radial section, revolved about the Z axis.
        pts = [V(0, 0, 0), V(r0-c, 0, 0), V(r0, 0, c),
               V(r0, 0, 40), V(rb, 0, 40), V(rb, 0, 90),
               V(rc, 0, 90), V(rc, 0, 100), V(rb, 0, 100),
               V(rb, 0, 140), V(re, 0, 140), V(re, 0, z-c),
               V(re-c, 0, z), V(0, 0, z), V(0, 0, 0)]
        obj.Shape = Part.Face(Part.makePolygon(pts)).revolve(V(0, 0, 0), V(0, 0, 1), 360)


class GrooveProxy:
    def execute(self, obj):
        base = obj.Source.Shape
        r_outer = float(obj.BearingDiameter) / 2.0 + 1.0
        r_floor = float(obj.GrooveDiameter) / 2.0
        cut = Part.makeCylinder(r_outer, float(obj.GrooveWidth), V(0, 0, float(obj.GrooveStart)))
        cut = cut.cut(Part.makeCylinder(r_floor, float(obj.GrooveWidth), V(0, 0, float(obj.GrooveStart))))
        obj.Shape = base.cut(cut)


class SplineProxy:
    def execute(self, obj):
        base = obj.Source.Shape
        major = float(obj.SplineMajorDiameter) / 2.0
        minor = float(obj.SplineMinorDiameter) / 2.0
        length = float(obj.SplineLength)
        chamfer = float(obj.EndChamfer)
        n = int(obj.NumberOfSplines)
        half_width = float(obj.ToothWidth) / 2.0
        # Remove the major-radius annulus over the spline length, leaving a core.
        removal = Part.makeCylinder(major + 2, length, V(0, 0, 0)).cut(
            Part.makeCylinder(minor, length, V(0, 0, 0)))
        result = base.cut(removal)
        # A chamfered cylindrical envelope gives each tooth tip the required 1 x 45 bevel.
        envpts = [V(0, 0, 0), V(major-chamfer, 0, 0), V(major, 0, chamfer),
                  V(major, 0, length), V(0, 0, length), V(0, 0, 0)]
        envelope = Part.Face(Part.makePolygon(envpts)).revolve(V(0, 0, 0), V(0, 0, 1), 360)
        teeth = None
        # Each rectangular strip has flat sides y = +/- tooth_width/2 in its radial frame.
        for i in range(n):
            tooth = Part.makeBox(major + 2, 2 * half_width, length,
                                 V(0, -half_width, 0))
            tooth.rotate(V(0, 0, 0), V(0, 0, 1), 360.0 * i / n)
            tooth = tooth.common(envelope)
            teeth = tooth if teeth is None else teeth.fuse(tooth)
        obj.Shape = result.fuse(teeth)


class KeywayProxy:
    def execute(self, obj):
        base = obj.Source.Shape
        floor = float(obj.FloorX)
        radius = float(obj.KeywayWidth) / 2.0
        xlen = float(obj.EndDiameter)  # safely passes entirely through the outer surface
        z1 = float(obj.FirstEndCenter)
        z2 = float(obj.SecondEndCenter)
        # Capsule in the YZ plane, extruded from its flat floor out of the +X side.
        cutter = Part.makeBox(xlen, 2 * radius, z2-z1, V(floor, -radius, z1))
        for zc in (z1, z2):
            cutter = cutter.fuse(Part.makeCylinder(radius, xlen, V(floor, 0, zc), V(1, 0, 0)))
        obj.Shape = base.cut(cutter)


class CrossHoleProxy:
    def execute(self, obj):
        base = obj.Source.Shape
        radius = float(obj.CrossHoleDiameter) / 2.0
        # Deliberately longer than the local 30 mm shaft diameter for a through hole.
        cutter = Part.makeCylinder(radius, 50, V(0, -25, float(obj.HoleCenterZ)), V(0, 1, 0))
        obj.Shape = base.cut(cutter)


def feature(body, name, label, proxy):
    obj = body.newObject("PartDesign::FeaturePython", name)
    obj.Label = label
    obj.Proxy = proxy
    return obj


doc = App.newDocument("SplinedDriveShaft")
body = doc.addObject("PartDesign::Body", "DriveShaftBody")
body.Label = "Splined Drive Shaft (Parametric Body)"

blank = feature(body, "BaseRevolution", "Base Revolution (Stepped Shaft)", BaseProfileProxy())
add_length(blank, "OverallLength", 175, "Overall shaft length")
add_length(blank, "SplineMajorDiameter", 25)
add_length(blank, "BearingDiameter", 30)
add_length(blank, "CollarDiameter", 40)
add_length(blank, "EndDiameter", 20)
add_length(blank, "EndChamfer", 1, "45 degree outer end chamfers")

groove = feature(body, "RetainingRingGroove", "Retaining Ring Groove", GrooveProxy())
groove.addProperty("App::PropertyLink", "Source", "Base")
groove.Source = blank
add_length(groove, "GrooveStart", 82)
add_length(groove, "GrooveWidth", 2)
add_length(groove, "GrooveDiameter", 28)
add_length(groove, "BearingDiameter", 30)

spline = feature(body, "SplineCut", "Straight-sided Spline", SplineProxy())
spline.addProperty("App::PropertyLink", "Source", "Base")
spline.Source = groove
add_length(spline, "SplineMajorDiameter", 25)
add_length(spline, "SplineMinorDiameter", 21)
add_integer(spline, "NumberOfSplines", 6)
add_length(spline, "SplineLength", 30)
add_length(spline, "ToothWidth", 6)
add_length(spline, "EndChamfer", 1)

key = feature(body, "KeywayPocket", "Keyway Pocket", KeywayProxy())
key.addProperty("App::PropertyLink", "Source", "Base")
key.Source = spline
add_length(key, "EndDiameter", 20)
add_length(key, "KeywayWidth", 6)
add_length(key, "KeywayDepth", 3.5)
add_length(key, "FloorX", 6.5, "Keyway floor location from shaft axis")
# Keep the floor tied to the requested depth: 10 - 3.5 = 6.5 mm.
key.setExpression("FloorX", "EndDiameter / 2 - KeywayDepth")
add_length(key, "FirstEndCenter", 148)
add_length(key, "SecondEndCenter", 167)

hole = feature(body, "CrossHole", "Cross Hole (Through All)", CrossHoleProxy())
hole.addProperty("App::PropertyLink", "Source", "Base")
hole.Source = key
add_length(hole, "CrossHoleDiameter", 5)
add_length(hole, "HoleCenterZ", 120)

doc.recompute()
for item in (blank, groove, spline, key):
    item.Visibility = False
hole.addProperty("App::PropertyString", "Description", "Documentation")
hole.Description = "5 mm diameter through hole along Y at Z = 120 mm"
body.Tip = hole
doc.recompute()

out_path = os.path.splitext(os.path.abspath(__file__))[0] + ".FCStd"
doc.recompute()
doc.saveAs(out_path)
