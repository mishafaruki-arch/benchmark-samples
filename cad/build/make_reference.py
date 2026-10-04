# Builds the reference FCStd for the flanged-bushing task.
import os

import FreeCAD as App, Part

doc = App.newDocument("FlangedBushing")
body = doc.addObject("PartDesign::Body", "Body")

def circle_sketch(name, diameter, z):
    s = body.newObject("Sketcher::SketchObject", name)
    s.AttachmentSupport = [(doc.getObject("XY_Plane"), "")]
    s.MapMode = "FlatFace"
    s.AttachmentOffset = App.Placement(App.Vector(0, 0, z), App.Rotation())
    s.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), diameter / 2))
    return s

flange = body.newObject("PartDesign::Pad", "FlangePad")
flange.Profile = circle_sketch("FlangeSketch", 50, 0)
flange.Length = 6
doc.recompute()

sleeve = body.newObject("PartDesign::Pad", "SleevePad")
sleeve.Profile = circle_sketch("SleeveSketch", 30, 6)
sleeve.Length = 24
doc.recompute()

bore = body.newObject("PartDesign::Pocket", "Bore")
bore.Profile = circle_sketch("BoreSketch", 20, 30)
bore.Type = 1  # through all
doc.recompute()

s = body.Shape
bb = s.BoundBox
print("SOLIDS", len(s.Solids), "VALID", s.isValid())
print("VOLUME %.4f AREA %.4f" % (s.Volume, s.Area))
print("BBOX %.3f x %.3f x %.3f" % (bb.XLength, bb.YLength, bb.ZLength))
doc.saveAs(os.environ.get("OUT", "/out/reference.FCStd"))
