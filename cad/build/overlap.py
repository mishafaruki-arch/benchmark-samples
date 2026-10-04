# Compares a candidate part to the reference by overlap volume: the volume
# inside one solid but not the other. 0 means the solids are identical.
#
#   REF=/ref/reference.FCStd CAND=/candidate/answer.FCStd freecadcmd overlap.py
import os

import FreeCAD as App


def solid(p):
    d = App.openDocument(p)
    return [o for o in d.Objects if o.TypeId == "PartDesign::Body"][0].Shape


ref = solid(os.environ.get("REF", "/ref/reference.FCStd"))
c = solid(os.environ.get("CAND", "/candidate/answer.FCStd"))
diff = ref.cut(c).Volume + c.cut(ref).Volume
print("OVERLAP mismatched volume = %.4f mm3 (%.4f%% of part)" % (diff, 100 * diff / ref.Volume))
