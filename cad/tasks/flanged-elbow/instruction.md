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

A 90 degree flanged pipe elbow: two identical square flanges on perpendicular planes, joined by straight pipe sections and a 90 degree bend. The part is hollow throughout, with a continuous bore of diameter pipe_inner_diameter. The pipe outside diameter is pipe_outer_diameter.

Inlet: the inlet flange lies on the XY plane from Z = 0 to Z = flange_thickness, centered on the Z axis. A straight pipe continues along the Z axis from the top of the flange to Z = 40.

Bend: from Z = 40 the pipe turns 90 degrees toward +X. The bend centerline is a quarter circle of radius 60 mm about an axis parallel to Y through the point (60, 0, 40), so the bend ends at X = 60 with its centerline at (60, 0, 100), now pointing along +X.

Outlet: a straight pipe continues along +X from X = 60 to X = 88, with its axis at Y = 0, Z = 100. The outlet flange is perpendicular to X, from X = 88 to X = 100, centered on that axis.

Flanges: each flange is a flange_width x flange_width square plate with its four corners rounded to radius flange_corner_radius, flange_thickness thick, centered on its pipe axis, with a central bore of diameter pipe_inner_diameter. Each flange has number_bolt_holes_per_flange through holes of diameter bolt_hole_diameter at the corners of a 60 mm square centered on its pipe axis: at (X, Y) = (+/-30, +/-30) on the inlet flange, and at (Y, Z) = (+/-30, 100 +/- 30) on the outlet flange.

**Key parameters:**

- pipe_outer_diameter = 40mm
- pipe_inner_diameter = 32mm
- flange_width = 80mm
- flange_thickness = 12mm
- flange_corner_radius = 8mm
- bolt_hole_diameter = 9mm
- number_bolt_holes_per_flange = 4
- overall_height = 140mm
- overall_length = 140mm

**FreeCAD version**: 1.1.0.

**Output location**: write your script to `/app/answer.py` and the generated model to `/app/answer.FCStd`. The verifier reads from these exact paths; files saved anywhere else are not graded.
