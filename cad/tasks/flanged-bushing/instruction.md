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

A flanged bushing consists of a circular flange, a cylindrical sleeve rising from one face of the flange, and a plain through bore running along the shared axis.

The flange is defined by flange_diameter and flange_thickness. The sleeve is coaxial with the flange and is defined by sleeve_diameter and sleeve_length, measured from the flange face to the end of the sleeve, so the overall length of the part is overall_length.

The through bore is defined by bore_diameter and passes through both the sleeve and the flange.

**Key parameters:**

- flange_diameter = 50mm
- flange_thickness = 6mm
- sleeve_diameter = 30mm
- sleeve_length = 24mm
- bore_diameter = 20mm
- overall_length = 30mm

**FreeCAD version**: 1.1.0.

**Output location**: write your script to `/app/answer.py` and the generated model to `/app/answer.FCStd`. The verifier reads from these exact paths; files saved anywhere else are not graded.
