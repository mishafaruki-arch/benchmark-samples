"""Determinism check: hash every mesh vertex a script produces.

Run it twice; a deterministic reference script prints the same hash both times.

    blender --background --python eval/mesh_hash.py -- tasks/Teapot_seed0/Teapot_seed0.py
"""
import hashlib
import runpy
import sys
import time

import bpy

script = sys.argv[sys.argv.index("--") + 1]
t0 = time.time()
runpy.run_path(script, run_name="__main__")
elapsed = time.time() - t0

h = hashlib.sha256()
n_verts = 0
for ob in sorted(bpy.context.scene.objects, key=lambda o: o.name):
    if ob.type != "MESH":
        continue
    for v in ob.data.vertices:
        h.update(("%.6f %.6f %.6f" % tuple(ob.matrix_world @ v.co)).encode())
        n_verts += 1

print(f"MESHHASH {h.hexdigest()[:16]}  verts={n_verts}  build_s={elapsed:.2f}")
