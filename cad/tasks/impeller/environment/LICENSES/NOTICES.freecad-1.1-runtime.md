# Third-Party Notices - FreeCAD 1.1 CAD Runtime

Generated cad-bench task images contain FreeCAD 1.1.0, its Python runtime, and
the scientific Python packages required by the geometry scorer. They do not
contain the CalculiX solver. Verifier images additionally contain the
gNucleus-authored `gnucleus-freecad-validator` package and task scripts.

The complete LGPL-2.1 text is distributed as `LGPL-2.1.txt` next to this file.
Recipients may obtain, modify, and replace the covered components under their
respective licenses using the upstream source locations below.

---

## FreeCAD

**Version:** 1.1.0 (packaged by conda-forge)
**Source:** https://github.com/FreeCAD/FreeCAD
**License:** GNU Lesser General Public License v2.1 (LGPL-2.1)
**License text:** `LGPL-2.1.txt`, or
https://github.com/FreeCAD/FreeCAD/blob/main/LICENSE-LGPL2.txt

FreeCAD is included unmodified as the parametric CAD runtime. Users may replace
it with a modified build and rebuild this OCI image under the LGPL terms.

---

## Open CASCADE Technology (OCCT)

**Version:** 7.9.3 (resolved by the conda-forge FreeCAD 1.1.0 package)
**Source:** https://dev.opencascade.org/
**License:** GNU Lesser General Public License v2.1 with the Open CASCADE
Exception
**License text:** https://dev.opencascade.org/license/lgpl_21.txt

OCCT is the geometric kernel used by FreeCAD. It is included unmodified through
the conda-forge dependency graph.

---

## Qt

**Source:** https://code.qt.io/cgit/
**License:** GNU Lesser General Public License v3.0, with portions also
available under GPL-3.0 with the Qt GPL Exception or a commercial license
**License text:** https://www.gnu.org/licenses/lgpl-3.0.txt

Qt components are included unmodified as dependencies of the conda-forge
FreeCAD package. The standard OCI build process permits recipients to replace
the libraries and rebuild the image.

---

## Coin3D

**Source:** https://github.com/coin3d/coin
**License:** BSD 3-Clause
**License text:** https://github.com/coin3d/coin/blob/master/COPYING

Copyright (C) by Kongsberg Oil & Gas Technologies. All rights reserved.

---

## Pivy

**Source:** https://github.com/coin3d/pivy
**License:** ISC License
**License text:** https://github.com/coin3d/pivy/blob/master/LICENSE

Pivy provides Python bindings for Coin3D and is included as a FreeCAD runtime
dependency.

---

## Python and scientific Python packages

The image includes Python 3.12, NumPy, SciPy, and Pydantic from conda-forge.
Their authoritative source and license locations are listed below.

- Python source and license: https://www.python.org/ and
  https://docs.python.org/3/license.html
- NumPy source and BSD license: https://github.com/numpy/numpy
- SciPy source and BSD license: https://github.com/scipy/scipy
- Pydantic source and MIT license: https://github.com/pydantic/pydantic

---

## gnucleus-freecad-validator

**Version:** 0.1.3 (verifier image only)
**Source:** https://github.com/gNucleus-AI/freecad-validator
**License:** Apache License 2.0
**License text:** `APACHE-2.0.txt`

---

## Ubuntu base system

**Source:** https://ubuntu.com/
**License:** Various free-software licenses

The underlying operating-system packages retain their package copyright files
under `/usr/share/doc/<package>/copyright`.

---

## About this image

**Image:** generated cad-bench text-to-CAD agent or verifier image
**Vendor:** gNucleus AI, Inc.
**Contents:** FreeCAD 1.1.0, OCCT 7.9.3, Python 3.12, NumPy, SciPy, Pydantic,
and their runtime dependencies.

These images are generated from public Dockerfile recipes in cad-bench. FEM
workflows are outside the scope of these task images.
