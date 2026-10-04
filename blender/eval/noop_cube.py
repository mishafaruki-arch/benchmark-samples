"""No-op baseline: a script that runs cleanly but builds the wrong thing.

A unit cube passes the parse and executability checks, so it marks the floor
every graded verifier must put it near. A verifier that scores this close to
the reference cannot tell a real answer from a trivial one.
"""
import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
