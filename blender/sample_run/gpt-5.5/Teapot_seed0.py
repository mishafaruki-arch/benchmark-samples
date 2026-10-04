import bpy
import math
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

ceramic_mat = bpy.data.materials.new("warm_untextured_ceramic")
ceramic_mat.diffuse_color = (0.86, 0.83, 0.76, 1.0)

created_objects = []


def smooth_object(obj):
    if obj and obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def add_material(obj, mat=ceramic_mat):
    obj.data.materials.append(mat)
    return obj


def catmull_rom_point(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    r = 0.5 * (
        (2.0 * p1[0]) +
        (-p0[0] + p2[0]) * t +
        (2.0 * p0[0] - 5.0 * p1[0] + 4.0 * p2[0] - p3[0]) * t2 +
        (-p0[0] + 3.0 * p1[0] - 3.0 * p2[0] + p3[0]) * t3
    )
    z = 0.5 * (
        (2.0 * p1[1]) +
        (-p0[1] + p2[1]) * t +
        (2.0 * p0[1] - 5.0 * p1[1] + 4.0 * p2[1] - p3[1]) * t2 +
        (-p0[1] + 3.0 * p1[1] - 3.0 * p2[1] + p3[1]) * t3
    )
    return (max(r, 0.0), z)


def sample_profile(control_points, samples_per_segment=8):
    out = []
    n = len(control_points)
    for i in range(n - 1):
        p0 = control_points[max(i - 1, 0)]
        p1 = control_points[i]
        p2 = control_points[i + 1]
        p3 = control_points[min(i + 2, n - 1)]
        for s in range(samples_per_segment):
            t = s / samples_per_segment
            if i > 0 or s > 0:
                out.append(catmull_rom_point(p0, p1, p2, p3, t))
            else:
                out.append(p1)
    out.append(control_points[-1])
    return out


def create_revolved_mesh(name, profile, segments=128):
    verts = []
    faces = []
    for r, z in profile:
        for j in range(segments):
            a = 2.0 * math.pi * j / segments
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(len(profile) - 1):
        for j in range(segments):
            j2 = (j + 1) % segments
            faces.append((i * segments + j, i * segments + j2, (i + 1) * segments + j2, (i + 1) * segments + j))
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    add_material(obj)
    smooth_object(obj)
    created_objects.append(obj)
    return obj


def cubic_bezier(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (u ** 3) * p0 + 3.0 * (u ** 2) * t * p1 + 3.0 * u * (t ** 2) * p2 + (t ** 3) * p3


def cubic_bezier_derivative(p0, p1, p2, p3, t):
    u = 1.0 - t
    return 3.0 * (u ** 2) * (p1 - p0) + 6.0 * u * t * (p2 - p1) + 3.0 * (t ** 2) * (p3 - p2)


def create_bezier_tube(name, p0, p1, p2, p3, radius_func, length_segments=48, radial_segments=32, cap_start=False, cap_end=False):
    verts = []
    faces = []
    rings = []
    world_y = Vector((0.0, 1.0, 0.0))

    for i in range(length_segments + 1):
        t = i / length_segments
        center = cubic_bezier(p0, p1, p2, p3, t)
        tangent = cubic_bezier_derivative(p0, p1, p2, p3, t)
        if tangent.length < 0.0001:
            tangent = Vector((1.0, 0.0, 0.0))
        tangent.normalize()

        v1 = world_y.copy()
        if abs(tangent.dot(v1)) > 0.97:
            v1 = Vector((0.0, 0.0, 1.0))
        v2 = tangent.cross(v1)
        if v2.length < 0.0001:
            v2 = Vector((0.0, 0.0, 1.0))
        v2.normalize()
        v1 = v2.cross(tangent)
        v1.normalize()

        r = radius_func(t)
        ring = []
        for j in range(radial_segments):
            a = 2.0 * math.pi * j / radial_segments
            point = center + v1 * (math.cos(a) * r) + v2 * (math.sin(a) * r)
            ring.append(len(verts))
            verts.append(tuple(point))
        rings.append(ring)

    for i in range(length_segments):
        for j in range(radial_segments):
            j2 = (j + 1) % radial_segments
            faces.append((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))

    if cap_start:
        faces.append(tuple(reversed(rings[0])))
    if cap_end:
        faces.append(tuple(rings[-1]))

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    add_material(obj)
    smooth_object(obj)
    created_objects.append(obj)
    return obj


def add_torus(name, location, major_radius, minor_radius, axis_direction=Vector((0.0, 0.0, 1.0)), major_segments=128, minor_segments=18):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=major_segments,
        minor_segments=minor_segments,
        major_radius=major_radius,
        minor_radius=minor_radius,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    q = axis_direction.normalized().to_track_quat('Z', 'Y')
    obj.rotation_euler = q.to_euler()
    add_material(obj)
    smooth_object(obj)
    created_objects.append(obj)
    return obj


def add_oval_boss(name, location, scale):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    add_material(obj)
    smooth_object(obj)
    created_objects.append(obj)
    return obj


body_controls = [
    (0.00, 0.10),
    (0.40, 0.085),
    (0.78, 0.095),
    (0.92, 0.18),
    (0.82, 0.30),
    (1.10, 0.48),
    (1.55, 0.76),
    (1.78, 1.05),
    (1.80, 1.28),
    (1.55, 1.58),
    (1.12, 1.80),
    (0.76, 1.93),
    (0.66, 2.02)
]
body_profile = sample_profile(body_controls, 7)
body = create_revolved_mesh("squat_round_belly_with_neck", body_profile, 144)

add_torus("low_rounded_foot_ring", (0.0, 0.0, 0.15), 0.72, 0.085, Vector((0.0, 0.0, 1.0)), 144, 18)
add_torus("rolled_upper_rim", (0.0, 0.0, 2.035), 0.78, 0.085, Vector((0.0, 0.0, 1.0)), 144, 20)

lid_controls = [
    (0.00, 2.205),
    (0.20, 2.225),
    (0.48, 2.190),
    (0.70, 2.125),
    (0.82, 2.085)
]
lid_profile = sample_profile(lid_controls, 9)
lid = create_revolved_mesh("shallow_domed_lid", lid_profile, 144)
add_torus("small_lid_seating_bead", (0.0, 0.0, 2.085), 0.72, 0.035, Vector((0.0, 0.0, 1.0)), 144, 12)

knob_controls = [
    (0.00, 2.205),
    (0.15, 2.210),
    (0.225, 2.245),
    (0.170, 2.285),
    (0.115, 2.305),
    (0.195, 2.335),
    (0.235, 2.375),
    (0.165, 2.425),
    (0.00, 2.445)
]
knob_profile = sample_profile(knob_controls, 8)
knob = create_revolved_mesh("small_turned_lid_knob", knob_profile, 128)
add_torus("knob_lower_turned_bead", (0.0, 0.0, 2.245), 0.185, 0.017, Vector((0.0, 0.0, 1.0)), 96, 10)
add_torus("knob_upper_turned_bead", (0.0, 0.0, 2.355), 0.205, 0.014, Vector((0.0, 0.0, 1.0)), 96, 10)

spout_p0 = Vector((1.38, 0.0, 0.88))
spout_p1 = Vector((1.95, 0.0, 0.86))
spout_p2 = Vector((2.32, 0.0, 1.55))
spout_p3 = Vector((3.28, 0.0, 1.58))


def spout_radius(t):
    if t < 0.82:
        u = t / 0.82
        return 0.33 * (1.0 - u) + 0.17 * u
    u = (t - 0.82) / 0.18
    u = max(0.0, min(1.0, u))
    s = u * u * (3.0 - 2.0 * u)
    return 0.17 * (1.0 - s) + 0.275 * s


spout = create_bezier_tube("long_curved_tapered_spout", spout_p0, spout_p1, spout_p2, spout_p3, spout_radius, 54, 36, False, False)
spout_base_t = 0.055
spout_base_center = cubic_bezier(spout_p0, spout_p1, spout_p2, spout_p3, spout_base_t)
spout_base_axis = cubic_bezier_derivative(spout_p0, spout_p1, spout_p2, spout_p3, spout_base_t)
add_torus("raised_spout_root_collar", tuple(spout_base_center), 0.365, 0.070, spout_base_axis, 96, 16)
spout_tip_axis = cubic_bezier_derivative(spout_p0, spout_p1, spout_p2, spout_p3, 1.0)
add_torus("slightly_flared_spout_lip", tuple(spout_p3), 0.275, 0.035, spout_tip_axis, 96, 12)

handle_p0 = Vector((-1.45, 0.0, 1.56))
handle_p1 = Vector((-2.62, 0.0, 1.62))
handle_p2 = Vector((-2.62, 0.0, 0.54))
handle_p3 = Vector((-1.46, 0.0, 0.68))


def handle_radius(t):
    end_thicken = max(0.0, 1.0 - min(t, 1.0 - t) / 0.18)
    end_thicken = end_thicken * end_thicken * (3.0 - 2.0 * end_thicken)
    return 0.155 + 0.035 * end_thicken


handle = create_bezier_tube("c_shaped_loop_handle", handle_p0, handle_p1, handle_p2, handle_p3, handle_radius, 62, 34, True, True)

add_oval_boss("upper_oval_handle_mount", (-1.55, 0.0, 1.56), (0.135, 0.42, 0.30))
add_oval_boss("lower_oval_handle_mount", (-1.48, 0.0, 0.68), (0.125, 0.39, 0.285))
add_torus("upper_handle_mount_raised_ring", (-1.61, 0.0, 1.56), 0.275, 0.047, Vector((1.0, 0.0, 0.0)), 96, 12)
add_torus("lower_handle_mount_raised_ring", (-1.54, 0.0, 0.68), 0.255, 0.045, Vector((1.0, 0.0, 0.0)), 96, 12)

bpy.ops.object.select_all(action='DESELECT')
for obj in created_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
teapot = bpy.context.object
teapot.name = "classic_ceramic_teapot"
teapot.data.name = "classic_ceramic_teapot_mesh"
for poly in teapot.data.polygons:
    poly.use_smooth = True
teapot.location = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()