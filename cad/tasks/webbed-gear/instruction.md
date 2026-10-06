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

A webbed spur gear consists of an involute toothed rim, a thinner web recessed equally from both faces, six round lightening holes through the web, and a central hub with a keyed through bore. The gear axis is the Z axis, with one face of the gear on the XY plane (Z = 0) and the other at Z = face_width.

Teeth: standard full-depth involute spur teeth with gear_module = 2mm, number_of_teeth = 36 and a 20 degree pressure angle, so the pitch diameter is 72mm and the base circle diameter is 72mm x cos(20 degrees). There is no profile shift and no backlash: the tooth thickness measured along the pitch circle is exactly half the circular pitch (pi x module / 2). Each tooth flank is a true involute of the base circle from the base circle up to the tip circle (tip_diameter). Because the root circle (root_diameter) is smaller than the base circle, each flank continues below the base circle as a straight radial line down to the root circle. The tooth tip is an arc on the tip circle, and the space between adjacent teeth is closed by an arc on the root circle (no root fillet, no tip chamfer). One tooth is centered on the +X axis.

Web: an annular recess is cut into each face of the gear between the hub (hub_diameter) and the inside of the rim (rim_inner_diameter). Both recesses have the same depth, leaving a centered web of thickness web_thickness. The hub keeps the full face_width.

Lightening holes: number_lightening_holes round through holes of diameter lightening_hole_diameter, equally spaced on a circle of diameter lightening_hole_pcd, with the first hole centered on the +X axis.

Bore and keyway: a through bore of diameter bore_diameter runs along the Z axis. A rectangular keyway of width 5mm, centered on the +Y axis and running the full face width, extends the bore so that the flat keyway floor lies 10.3mm from the gear axis.

**Key parameters:**

- number_of_teeth = 36
- tip_diameter = 76mm
- root_diameter = 67mm
- face_width = 20mm
- web_thickness = 8mm
- rim_inner_diameter = 56mm
- hub_diameter = 30mm
- bore_diameter = 16mm
- lightening_hole_diameter = 10mm
- number_lightening_holes = 6
- lightening_hole_pcd = 43mm

**FreeCAD version**: 1.1.0.

**Output location**: write your script to `/app/answer.py` and the generated model to `/app/answer.FCStd`. The verifier reads from these exact paths; files saved anywhere else are not graded.
