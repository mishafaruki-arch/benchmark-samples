import bpy
import bmesh
import random
from math import pi, cos, sin
from mathutils import Vector

# ── Seeds ──
# FACTORY_SEED drives parameter sampling (proportions); geometry is fully
# determined by those parameters, so one seed is enough here.
FACTORY_SEED = 0
rng = random.Random(FACTORY_SEED)

# ── Scene cleanup ──
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes):
    bpy.data.meshes.remove(m)
for c in list(bpy.data.collections):
    if c != bpy.context.scene.collection:
        bpy.data.collections.remove(c)
bpy.context.scene.cursor.location = (0, 0, 0)

# ── Parameters (sampled once per seed) ──
BODY_RADIUS   = rng.uniform(0.95, 1.05)   # widest radius of the belly
BODY_HEIGHT   = rng.uniform(1.05, 1.20)   # foot to rim
BELLY_Z       = rng.uniform(0.40, 0.48)   # widest point, as fraction of height
SPOUT_REACH   = rng.uniform(0.75, 0.90)   # horizontal reach past the belly
SPOUT_RISE    = rng.uniform(0.95, 1.05)   # tip height, as fraction of height
HANDLE_REACH  = rng.uniform(0.45, 0.55)   # how far the handle loops out
KNOB_HEIGHT   = rng.uniform(0.14, 0.18)
RING_SEGMENTS = 64

SCALE = 1.0   # unit-scale model (~3.5 units across); the eval renderer's
              # lamps have fixed wattage, so tiny objects render blown out


# ── Utilities ──

def catmull_rom(points, samples_per_seg=8):
    """Smooth a 2D polyline through its control points (endpoints kept)."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = (Vector(pts[j]) for j in (i - 1, i, i + 1, i + 2))
        for s in range(samples_per_seg):
            t = s / samples_per_seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t
                              + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(points[-1]))
    return out


def lathe(name, profile, segments=RING_SEGMENTS):
    """Revolve a (radius, z) profile around Z into a mesh object."""
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=2 * pi, steps=segments, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    return finish(name, bm)


def bezier(p0, p1, p2, p3, n):
    p0, p1, p2, p3 = (Vector(p) for p in (p0, p1, p2, p3))
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append(u ** 3 * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t ** 3 * p3)
    return out


def sweep_tube(name, path, radius_fn, aspect=1.0, segments=24, cap_ends=False):
    """Sweep a circular/elliptical section along a path lying in the XZ plane.

    radius_fn(t) gives the radius at t in [0, 1]; `aspect` stretches the
    section along Y (the axis perpendicular to the path's plane).
    """
    bm = bmesh.new()
    side = Vector((0, 1, 0))
    rings = []
    n = len(path)
    for i, c in enumerate(path):
        tangent = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        normal = side.cross(tangent).normalized()
        r = radius_fn(i / (n - 1))
        ring = []
        for k in range(segments):
            a = 2 * pi * k / segments
            ring.append(bm.verts.new(c + normal * (r * cos(a)) + side * (r * aspect * sin(a))))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(segments):
            k2 = (k + 1) % segments
            bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    if cap_ends:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    return finish(name, bm)


def finish(name, bm):
    # Bake the real-world scale into the vertices so no transform is left over.
    bmesh.ops.scale(bm, vec=(SCALE, SCALE, SCALE), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ── Body: revolved profile with foot ring, round belly, shoulder and rim ──
R, H = BODY_RADIUS, BODY_HEIGHT
neck_r = 0.58 * R
body_ctrl = [
    (0.00,         0.00),
    (0.56 * R,     0.00),
    (0.64 * R,     0.01),       # foot ring: short flared band...
    (0.65 * R,     0.07),
    (0.58 * R,     0.09),       # ...with a visible step in to the belly
    (0.80 * R,     0.17 * H),
    (R,            BELLY_Z * H),  # widest point
    (0.93 * R,     0.70 * H),
    (0.76 * R,     0.86 * H),   # shoulder
    (neck_r,       0.94 * H),
    (neck_r + 0.03, 0.98 * H),  # rolled rim
    (neck_r - 0.02, 1.00 * H),
    (neck_r - 0.05, 0.96 * H),  # inner lip the lid rests on
]
body = lathe("Teapot_Body", catmull_rom(body_ctrl, 10))

# ── Lid: shallow dome sitting in the rim, with a turned knob ──
lid_r = neck_r - 0.04
lid_ctrl = [
    (0.00,          0.95 * H),
    (lid_r,         0.95 * H),
    (lid_r + 0.01,  0.99 * H),
    (0.80 * lid_r,  1.05 * H),
    (0.45 * lid_r,  1.10 * H),
    (0.16,          1.12 * H),
    (0.09,          1.13 * H),   # knob stem
    (0.08,          1.13 * H + 0.4 * KNOB_HEIGHT),
    (0.14,          1.13 * H + 0.7 * KNOB_HEIGHT),  # knob bulb
    (0.10,          1.13 * H + 0.95 * KNOB_HEIGHT),
    (0.00,          1.13 * H + KNOB_HEIGHT),
]
lid = lathe("Teapot_Lid", catmull_rom(lid_ctrl, 8))

# ── Spout: tapering tube rising from the lower belly, flared at the tip ──
spout_base = (0.80 * R, 0.0, 0.28 * H)
spout_tip = (R + SPOUT_REACH, 0.0, SPOUT_RISE * H)
spout_path = bezier(spout_base,
                    (R + 0.35 * SPOUT_REACH, 0.0, 0.30 * H),
                    (R + 0.55 * SPOUT_REACH, 0.0, 0.70 * H),
                    spout_tip, 32)


def spout_radius(t):
    taper = 0.24 - 0.14 * t
    flare = 0.03 * max(0.0, (t - 0.88) / 0.12)
    return (taper + flare) * R


spout = sweep_tube("Teapot_Spout", spout_path, spout_radius)

# ── Handle: C-shaped loop on the opposite side, flattened oval section ──
handle_top = (-0.86 * R, 0.0, 0.76 * H)
handle_bot = (-0.92 * R, 0.0, 0.22 * H)
handle_path = bezier(handle_top,
                     (-(R + HANDLE_REACH * 1.6), 0.0, 0.92 * H),
                     (-(R + HANDLE_REACH * 1.4), 0.0, 0.10 * H),
                     handle_bot, 40)
handle = sweep_tube("Teapot_Handle", handle_path, lambda t: 0.075 * R,
                    aspect=1.6, cap_ends=True)
