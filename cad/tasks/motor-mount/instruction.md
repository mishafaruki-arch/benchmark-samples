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

A motor mount from a laser cutter gantry: a thick C-shaped aluminum plate with an open motor bore, two mounting ears with cross-drilled holes, and four blind tapped-hole drillings on a bolt circle.

Coordinates: the plate lies in the XY plane with its thickness along +Z. The front face is at Z = 0 and the back face at Z = plate_thickness. The part is symmetric about the XZ plane (Y = 0).

Profile (sharp corners before rounding): the left edge is X = -30 from Y = -30 to Y = 30. The top and bottom edges are Y = +30 and Y = -30, from X = -30 to X = 22. Two ears rise from these edges: each ear's inner edge is X = 22 (from |Y| = 30 to |Y| = 55), its end is |Y| = 55 (from X = 22 to X = 32), and its outer edge is X = 32 (from |Y| = 55 down to |Y| = 25). From (32, 25) a 45 degree edge runs to (27, 20), and the mirrored edge runs from (32, -25) to (27, -20). Two jaw edges then run along Y = +20 and Y = -20 from X = 27 toward -X until they meet a circle of diameter bore_diameter centered on the origin. That circle forms the motor bore: the bore arc closes the profile on the left, passing through (-25.125, 0), so the bore is open toward +X between the two jaws (a 40 mm wide opening).

Rounding: all vertical edges at the following profile corners are rounded with radius corner_radius: the two outer left corners (-30, +/-30), the two inside corners where the plate meets the ears (22, +/-30), the corners (32, +/-25), the corners (27, +/-20), and the two corners where each jaw edge meets the bore circle. The four ear end corners (22, +/-55) and (32, +/-55) are rounded with radius 0.5 mm. All other edges are sharp (no chamfers).

Blind holes: number_mounting_holes holes are centered on a circle of diameter mounting_hole_pcd around the Z axis, at 45, 135, 225 and 315 degrees from +X. From the front face (Z = 0) each position has a front_hole_diameter hole whose cylindrical part is front_hole_depth deep, ending in a 118 degree conical drill point (tip 12.4 mm from the front face). From the back face (Z = plate_thickness) each position has a back_hole_diameter hole whose cylindrical part is back_hole_depth deep, ending in a 118 degree conical drill point (tip 10.1 mm from the back face). The front and back holes do not meet.

Ear holes: each ear has two through holes of diameter ear_hole_diameter drilled along X through the full ear width (X = 22 to X = 32), centered at |Y| = 51 and at Z = 6.5 and Z = 18.5 (four ear holes in total).

**Key parameters:**

- overall_length = 110mm
- overall_width = 62mm
- plate_thickness = 25mm
- bore_diameter = 50.25mm
- corner_radius = 3.5mm
- number_mounting_holes = 4
- mounting_hole_pcd = 70mm
- front_hole_diameter = 4.2mm
- front_hole_depth = 11.138mm
- back_hole_diameter = 3.3mm
- back_hole_depth = 9.109mm
- ear_hole_diameter = 5.5mm

**FreeCAD version**: 1.1.0.

**Output location**: write your script to `/app/answer.py` and the generated model to `/app/answer.FCStd`. The verifier reads from these exact paths; files saved anywhere else are not graded.
