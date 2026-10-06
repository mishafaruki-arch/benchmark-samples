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

A splined stepped drive shaft with a retaining-ring groove, a keyway and a cross hole. The shaft axis is the Z axis; the spline end face is on the XY plane (Z = 0) and the keyed end is at Z = overall_length.

Stepped body (a solid of revolution about Z): diameter spline_major_diameter from Z = 0 to Z = 40; diameter bearing_diameter from Z = 40 to Z = 90; a collar of diameter collar_diameter from Z = 90 to Z = 100; diameter bearing_diameter again from Z = 100 to Z = 140; and diameter end_diameter from Z = 140 to Z = overall_length. Both end faces have a 1 mm x 45 degree chamfer on their outer edge (so the Z = 0 face has diameter 23 and the Z = 175 face has diameter 18). All other edges are sharp.

Retaining-ring groove: a rectangular groove 2 mm wide, from Z = 82 to Z = 84, cut into the first bearing_diameter step down to diameter groove_diameter.

Spline: number_of_splines straight-sided teeth on the spline_major_diameter step, from Z = 0 to Z = spline_length. Each tooth is 6 mm wide and is bounded by two flat sides parallel to the tooth's radial center plane, 3 mm on each side of it. One tooth is centered on the +X axis and the others are every 60 degrees. Between the teeth, material is removed down to diameter spline_minor_diameter. The spaces end flat at Z = spline_length (no run-out), and the 1 mm end chamfer remains on the tooth tips.

Keyway: on the +X side of the end_diameter step, a keyway 6 mm wide (sides at Y = -3 and Y = +3) with a flat floor at X = 6.5, i.e. keyway_depth below the top of the 20 mm diameter. It has rounded ends of radius 3 mm whose centers are at Z = 148 and Z = 167, so it spans Z = 145 to Z = 170.

Cross hole: a through hole of diameter cross_hole_diameter along the Y axis, centered at Z = 120 on the shaft axis, through the second bearing_diameter step.

**Key parameters:**

- overall_length = 175mm
- spline_major_diameter = 25mm
- spline_minor_diameter = 21mm
- number_of_splines = 6
- spline_length = 30mm
- bearing_diameter = 30mm
- collar_diameter = 40mm
- groove_diameter = 28mm
- end_diameter = 20mm
- keyway_depth = 3.5mm
- cross_hole_diameter = 5mm

**FreeCAD version**: 1.1.0.

**Output location**: write your script to `/app/answer.py` and the generated model to `/app/answer.FCStd`. The verifier reads from these exact paths; files saved anywhere else are not graded.
