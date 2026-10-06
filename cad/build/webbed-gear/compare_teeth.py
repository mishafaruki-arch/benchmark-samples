# Compares a candidate gear's tooth profile with the reference, independent of
# the validator. Prints the tooth width at the root, base, pitch and tip
# circles, and saves an overlay of both cross-sections at mid-height.
#
#   REF=/ref/reference.FCStd CAND=/candidate/answer.FCStd PNG=/out/teeth.png \
#       freecadcmd compare_teeth.py
import math
import os

import FreeCAD as App, Part
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

V = App.Vector
Z_MID = 10.0


def body_shape(p):
    d = App.openDocument(p)
    return [o for o in d.Objects if o.TypeId == "PartDesign::Body" and o.Shape.Solids][0].Shape


def outer_wire(s):
    return max(s.slice(V(0, 0, 1), Z_MID), key=lambda w: w.BoundBox.DiagonalLength)


def tooth_widths(s):
    face = Part.Face(outer_wire(s))
    out = []
    for name, r in (("root", 33.55), ("base", 33.83), ("pitch", 36.0), ("tip", 37.95)):
        arcs = Part.Edge(Part.Circle(V(0, 0, Z_MID), V(0, 0, 1), r)).common(face).Edges
        out.append((name, r, sum(e.Length for e in arcs) / max(len(arcs), 1)))
    return out


ref = body_shape(os.environ.get("REF", "/ref/reference.FCStd"))
cand = body_shape(os.environ.get("CAND", "/candidate/answer.FCStd"))

print("TEETH width at mid-height (average arc inside material per tooth)")
for (name, r, wr), (_, _, wc) in zip(tooth_widths(ref), tooth_widths(cand)):
    print("TEETH %-5s r=%.2f  reference=%.3f mm  candidate=%.3f mm" % (name, r, wr, wc))

fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
for ax, zoom in zip(axes, (False, True)):
    for s, color, lw, label in ((ref, "#1f77b4", 2.2, "Reference"), (cand, "#d62728", 1.4, "Candidate")):
        for i, e in enumerate(outer_wire(s).Edges):
            pts = e.discretize(max(2, int(e.Length / 0.05)))
            ax.plot([p.x for p in pts], [p.y for p in pts], color=color, lw=lw, label=label if i == 0 else None)
    for r in (33.5, 36.0, 38.0):
        t = [i * 2 * math.pi / 720 for i in range(721)]
        ax.plot([r * math.cos(a) for a in t], [r * math.sin(a) for a in t], ls=":", lw=0.8, color="gray")
    ax.set_aspect("equal")
    if zoom:
        ax.set_xlim(32.5, 39)
        ax.set_ylim(-4.5, 4.5)
        ax.set_title("Zoom: teeth on +X (dotted: root, pitch, tip circles)")
    else:
        ax.set_xlim(-40, 40)
        ax.set_ylim(-40, 40)
        ax.set_title("Cross-section at Z = %g mm" % Z_MID)
    ax.legend(loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(os.environ.get("PNG", "/out/teeth.png"), dpi=150)
print("SAVED", os.environ.get("PNG", "/out/teeth.png"))
