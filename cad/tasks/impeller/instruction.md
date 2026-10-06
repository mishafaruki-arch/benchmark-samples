Write a FreeCAD Python script to `answer.py` that reproduces the
part described below.

The model must be built as a parametric feature tree inside a single PartDesign Body,
producing exactly one solid body. Use editable PartDesign features to construct the
model for better parameterization.The saved FCStd must contain named document objects
whose properties drive the geometry, not a single Part::Feature holding
a pre-computed TopoShape.

Save the generated model as an `.FCStd` file next to the script, using
the script stem as the output basename. The output path must be derived
from `__file__` at runtime; do not hardcode the path or rely on the
current working directory. Only the FCStd written next to the executing
script file is graded.

**Part description:**

A radial impeller with a back plate, a central hub, seven backward-curved blades and a D-shaped bore. The impeller axis is the Z axis, with the back of the back plate on the XY plane (Z = 0).

Back plate: a disc of diameter backplate_diameter and thickness backplate_thickness, from Z = 0 to Z = 4.

Hub: a cylinder of diameter hub_diameter from Z = 4 to Z = 28, followed by a cone that tapers from diameter 30 at Z = 28 to diameter 16 at Z = overall_height, which is a flat top.

Blades: number_of_blades identical blades stand on the back plate, each blade_height tall (Z = 4 to Z = 24). Each blade is a vertical extrusion of a curved strip of constant thickness 3 mm. For the first blade, the strip lies between two concentric circular arcs of radius 48.5 and 51.5 centered at (X, Y) = (0, 50), and the blade is the part of that strip with X >= 0 that is outside the hub and inside a circle of diameter blade_tip_diameter centered on the axis. So each blade starts at the hub surface near the +X axis, curves toward +Y, and its outer end is cut by the blade_tip_diameter circle. The other blades are copies of the first, rotated about the Z axis by multiples of 360/7 degrees.

Bore: a D-shaped through bore along the Z axis: a circle of diameter bore_diameter with a flat on the +X side at X = 4 (the region of the circle with X > 4 is not cut).

**Key parameters:**

- backplate_diameter = 120mm
- backplate_thickness = 4mm
- hub_diameter = 30mm
- overall_height = 36mm
- number_of_blades = 7
- blade_height = 20mm
- blade_tip_diameter = 116mm
- bore_diameter = 10mm

**FreeCAD version**: 1.1.0.

**Output location**: write your script to `/app/answer.py` and the generated model to `/app/answer.FCStd`. The verifier reads from these exact paths; files saved anywhere else are not graded.
