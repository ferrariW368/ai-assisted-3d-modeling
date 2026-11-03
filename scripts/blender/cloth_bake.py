"""Cloth-wrinkle baking helpers for a garment mesh (run inside Blender, tested on 5.2).

Idea: the web viewer keeps its own low-poly garment mesh and UVs. That mesh is
exported to JSON, simulated here as cloth on a subdivided copy, and the
wrinkles are baked back onto the ORIGINAL low-poly UVs as a tangent-space
normal map plus an ambient-occlusion map. Because mesh and UVs are unchanged,
printed graphics on the garment do not shift.

Input JSON per garment (<BAKE_DIR>/<key>.json):
    {"body":   {"pos": [x,y,z,...], "uv": [u,v,...], "idx": [i,j,k,...]},
     "sleeve": {...}}            # three.js convention: Y up

Typical session (Blender Python console or an MCP exec call):
    import os; os.environ["BAKE_DIR"] = "/path/to/bake"
    exec(open("cloth_bake.py").read())
    low, sleeve = prep("shirt")
    hi = body_sim(low, "shirt_body_hi")
    sim = freeze(hi, "shirt_body_sim")
    bake(low, sim, "shirt-body-normal", 1024, 512, "NORMAL")
    bake(low, sim, "shirt-body-ao", 1024, 512, "AO", samples=48)
Then run postprocess_bake_maps.py on the PNGs.
"""
import json
import math
import os
import time

import bmesh
import bpy

BAKE = os.environ.get("BAKE_DIR", os.path.join(os.getcwd(), "bake"))


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)


def mk(name, d):
    """Build a mesh object from pos/uv/idx arrays (three.js Y-up -> Blender Z-up)."""
    p, uv, idx = d["pos"], d["uv"], d["idx"]
    verts = [(p[i], -p[i + 2], p[i + 1]) for i in range(0, len(p), 3)]
    faces = [(idx[i], idx[i + 1], idx[i + 2]) for i in range(0, len(idx), 3)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ul = me.uv_layers.new(name="UV")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            ul.data[li].uv = (uv[vi * 2], uv[vi * 2 + 1])
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    # Weld seams: merge coincident vertices (UV seams survive on the loops).
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for f in me.polygons:
        f.use_smooth = True
    return ob


def load(key):
    with open(os.path.join(BAKE, f"{key}.json"), encoding="utf-8") as f:
        return json.load(f)


def vert_v(me):
    """UV v coordinate per vertex (top of garment = 1, hem = 0)."""
    ul = me.uv_layers[0].data
    out = [0.0] * len(me.vertices)
    for loop in me.loops:
        out[loop.vertex_index] = ul[loop.index].uv[1]
    return out


def dup(ob, name):
    o2 = ob.copy()
    o2.data = ob.data.copy()
    o2.name = o2.data.name = name
    bpy.context.collection.objects.link(o2)
    return o2


def subdivide(ob, cuts=1):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True, smooth=1.0)
    bm.to_mesh(ob.data)
    bm.free()
    for f in ob.data.polygons:
        f.use_smooth = True


def shrink(ob, d):
    ob.data.update()
    for v in ob.data.vertices:
        v.co -= v.normal * d


def smoothstep(a, c, x):
    if x <= a:
        return 0.0
    if x >= c:
        return 1.0
    t = (x - a) / (c - a)
    return t * t * (3 - 2 * t)


def pin_group(ob, fn):
    vv = vert_v(ob.data)
    g = ob.vertex_groups.new(name="pin")
    for i, v in enumerate(vv):
        w = fn(v)
        if w > 0:
            g.add([i], min(1.0, w), "REPLACE")
    return g


def setup_cloth(ob, grow=0.05, frames=40):
    md = ob.modifiers.new("Cloth", "CLOTH")
    s = md.settings
    s.quality = 6
    s.mass = 0.15
    s.air_damping = 1.0
    s.tension_stiffness = s.compression_stiffness = 12
    s.shear_stiffness = 6
    s.bending_stiffness = 0.15
    s.vertex_group_mass = "pin"
    s.pin_stiffness = 1.0
    s.shrink_min = -grow  # negative shrink = fabric grows, so it has slack to fold
    c = md.collision_settings
    c.distance_min = 0.003
    c.use_self_collision = False
    md.point_cache.frame_start = 1
    md.point_cache.frame_end = frames
    return md


def collider(ob):
    ob.modifiers.new("Collision", "COLLISION")
    ob.collision.thickness_outer = 0.004
    ob.collision.cloth_friction = 5
    ob.hide_render = True


def run(frames):
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, frames
    for f in range(1, frames + 1):
        sc.frame_set(f)


def freeze(ob, name):
    """Apply the simulated state of frame N as a new static mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    o2 = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o2)
    return o2


def body_sim(low, name, frames=60, grow=0.04, top=(0.66, 0.88), neck=0.55,
             coldist=0.001, bending=1.0, grow_top=None):
    """Subdivided copy of the body; shoulders and tucked-in hem pinned, lower part gets slack."""
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    hi = dup(low, name)
    hi.hide_set(False)
    hi.location = low.location
    subdivide(hi, 1)
    pin_group(hi, lambda v: max(smoothstep(*top, v), 1 - smoothstep(0.015, 0.07, v)))
    vv = vert_v(hi.data)
    g = hi.vertex_groups.new(name="nogrow")
    for i, vt in enumerate(hi.data.vertices):
        ang = abs(math.atan2(vt.co.x, -vt.co.y))  # 0 = front centre
        w = max(smoothstep(top[0] - 0.1, top[0], vv[i]),
                smoothstep(neck, neck + 0.12, vv[i]) * (1 - smoothstep(0.6, 1.1, ang)))
        if grow_top:  # only the part below grow_top may loosen
            w = max(w, smoothstep(grow_top - 0.12, grow_top, vv[i]))
        if w > 0:
            g.add([i], w, "REPLACE")
    md = setup_cloth(hi, grow=grow, frames=frames)
    s = md.settings
    s.bending_stiffness = bending
    s.bending_damping = 0.5
    s.vertex_group_shrink = "nogrow"
    s.shrink_max = 0.0
    md.collision_settings.distance_min = coldist
    t = time.time()
    run(frames)
    print(name, "sim", round(time.time() - t, 1), "s")
    return hi


def bake(low, hi, out, w, h, kind="NORMAL", extrusion=0.03, ray=0.06, samples=1):
    """Selected-to-active bake from hi onto low's UVs. kind: NORMAL | AO. Writes <BAKE>/<out>.png."""
    sc = bpy.context.scene
    try:
        sc.render.engine = "CYCLES"
    except TypeError as e:  # message lists valid engines
        print(e)
    sc.cycles.samples = samples
    img = bpy.data.images.new(out, w, h, alpha=False, float_buffer=False)
    if kind == "NORMAL":
        img.colorspace_settings.name = "Non-Color"
    mat = bpy.data.materials.new("bake_" + out)
    mat.use_nodes = True
    tn = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tn.image = img
    mat.node_tree.nodes.active = tn
    low.data.materials.clear()
    low.data.materials.append(mat)
    if not hi.data.materials:
        hi.data.materials.append(bpy.data.materials.new("hi"))
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in (low, hi):
        o.hide_set(False)
        o.hide_render = False
    hi.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    b = sc.render.bake
    b.use_selected_to_active = True
    b.cage_extrusion = extrusion
    b.max_ray_distance = ray
    b.margin = 8
    if kind == "NORMAL":
        b.normal_space = "TANGENT"
    t = time.time()
    bpy.ops.object.bake(type=kind)
    img.filepath_raw = os.path.join(BAKE, f"{out}.png")
    img.file_format = "PNG"
    img.save()
    print(out, kind, round(time.time() - t, 1), "s")
    return img


def shift_u(ob, du):
    for d in ob.data.uv_layers[0].data:
        d.uv[0] += du


def prep(key, du_body=-0.25):
    """Clean scene: low-poly body (UV shifted into 0..1), sleeve, and a collider shrunk 14 mm inward."""
    clear()
    d = load(key)
    body = mk(key + "_body_low", d["body"])
    sleeve = mk(key + "_sleeve_low", d["sleeve"])
    shift_u(body, du_body)  # undone later in postprocess_bake_maps.py
    col = dup(body, key + "_body_col")
    shrink(col, 0.014)
    collider(col)
    col.collision.thickness_outer = 0.002
    col.hide_set(True)
    return body, sleeve
