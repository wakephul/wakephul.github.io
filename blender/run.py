"""Build the room and render / bake it.

  Blender -b -P blender/run.py -- --render out.png            preview still
  Blender -b -P blender/run.py -- --bake 4096 --samples 64    baked textures + room.glb in assets/
Options: --paint home|open|colour (what is white in the preview), --view AZIM,ELEV,DIST,
--res WxH, --cutouts PX, --blend (also save room.blend)
"""
import argparse
import json
import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib  # noqa: E402
import room  # noqa: E402

ASSETS = os.path.join(HERE, "..", "assets")
# A bake writes here first and moves everything into assets/ at the very end: textures and model
# must change together, or a page loaded halfway paints the new texture on the old model.
STAGE = os.path.join(HERE, "_out")


def cycles(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    sc.cycles.device = "GPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.denoising_use_gpu = True   # on the CPU, denoising a 4096 px bake took most of an hour
    sc.cycles.max_bounces = 8
    sc.view_settings.view_transform = room.VIEW_TRANSFORM
    sc.view_settings.look = room.LOOK


def render(path, res):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = os.path.abspath(path)
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)


# The web viewer keeps the camera inside these limits (see js/main.js), so anything that
# cannot be seen from there never needs texels or triangles.
AZIM, ELEV = (2, 88), (5, 62)


def cull(objs):
    """Move the faces no camera position can see into '<name>_hidden' objects: they still cast
    shadows and bounce light during the bake, but are neither baked nor exported."""
    verts, polys = [], []
    for o in objs:
        base = len(verts)
        verts += [v.co.copy() for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    bvh = BVHTree.FromPolygons(verts, polys)

    def orbit(target, dist, azims, elevs):
        for az in azims:
            for el in elevs:
                a, e = math.radians(az), math.radians(el)
                yield Vector(target) + dist * Vector((math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)))

    az5 = [AZIM[0] - 2, 24, 45, 66, AZIM[1] + 2]
    el3 = [ELEV[0] - 3, 30, ELEV[1] + 3]
    cams = list(orbit(room.TARGET, room.VIEW[2], az5, el3)) + list(orbit(room.TARGET, 6.5, az5, el3))
    for o in objs:   # close-ups on the clickable things
        if o.name != "room":
            c = sum((Vector(b) for b in o.bound_box), Vector()) / 8
            cams += list(orbit(c, 3.5, (az5[0], 45, az5[-1]), (el3[0], el3[-1])))

    total = hidden_n = 0
    for o in objs:
        me = o.data
        hidden = set()
        for p in me.polygons:
            pts = [p.center]
            if p.area > 2e-4:   # big faces can be partly covered: also try near the rim and halfway
                vs = [me.vertices[i].co for i in p.vertices]
                vs = vs[:: max(1, len(vs) // 16)]
                pts += [p.center.lerp(v, k) for k in (0.97, 0.5) for v in vs]
            n = p.normal
            seen = False
            for q in pts:
                q = q + n * 2e-4
                for cam in cams:
                    d = cam - q
                    if d.dot(n) <= 0:
                        continue
                    ln = d.length
                    if bvh.ray_cast(q, d / ln, ln)[0] is None:
                        seen = True
                        break
                if seen:
                    break
            if not seen:
                hidden.add(p.index)
        total += len(me.polygons)
        hidden_n += len(hidden)
        if not hidden:
            continue
        b = o.copy()
        b.data = me.copy()
        b.name = o.name + "_hidden"
        bpy.context.scene.collection.objects.link(b)
        for obj, keep_hidden in ((o, False), (b, True)):
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.index in hidden) != keep_hidden], context="FACES")
            bm.to_mesh(obj.data)
            bm.free()
    print(f"[run] culled {hidden_n} of {total} faces that are never visible")


def unwrap(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        if not o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in objs:  # more texels for the things people look at closely
        f = lib.UV_SCALE.get(o.name, 1.0)
        if f != 1.0:
            for l in o.data.uv_layers.active.data:
                l.uv *= f
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0015)
    bpy.ops.object.mode_set(mode="OBJECT")


def bake(objs, size, mode):
    """One texture per state, same UVs: "home" (room in colour, things white) and "open" (the opposite).
    The web page fades each piece from one to the other."""
    sc = bpy.context.scene
    lib.paint(mode)
    img = bpy.data.images.new(f"baked-{mode}", size, size, alpha=False, float_buffer=True)
    # start from grey, not black: slivers thinner than a texel never get baked and would show as dark specks
    img.generated_color = (0.35, 0.35, 0.34, 1.0)
    for m in bpy.data.materials:
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = img
        m.node_tree.nodes.active = n
    sc.render.bake.margin = max(4, size // 256)
    bpy.ops.object.bake(type="COMBINED", use_clear=False)
    sc.render.image_settings.file_format = "WEBP"
    sc.render.image_settings.quality = 88
    img.save_render(os.path.join(STAGE, f"baked-{mode}.webp"), scene=sc)
    img.scale(size // 2, size // 2)   # phones load this one
    img.save_render(os.path.join(STAGE, f"baked-{mode}-{size // 2}.webp"), scene=sc)


def export(objs):
    for o in objs:
        o.data.materials.clear()
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(STAGE, "room.glb"), export_format="GLB", use_selection=True,
        export_materials="NONE", export_normals=False, export_texcoords=True,
        export_apply=True, export_yup=True, export_animations=False,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
        export_draco_position_quantization=14, export_draco_texcoord_quantization=16,
    )
    x, y, z = room.TARGET   # camera framing for the web viewer, in three.js axes (y up)
    with open(os.path.join(STAGE, "room.json"), "w") as f:
        json.dump({"target": [x, z, -y], "azim": room.VIEW[0], "elev": room.VIEW[1], "dist": room.VIEW[2],
                   "azimLimits": AZIM, "elevLimits": ELEV, "v": int(time.time())}, f)   # v: cache-buster


# Collage cut-outs of the clickable things for the web cards: (azimuth, elevation, which part).
CUTOUTS = {
    "guitar": (8, 4, None), "bike": (58, 8, None), "shoes": (38, 28, None),
    "basketball": (35, 22, lambda box: max(p.z for p in box) < 0.6),   # just the ball
    "juggling": (40, 38, None), "cards": (25, 62, None), "bookshelf": (72, 8, None),
    "notebook": (30, 55, None), "whiteboard": (6, 2, None), "computer": (22, 16, None),
}


def cutouts(res):
    """Render each clickable thing alone, in colour, on a transparent background."""
    sc = bpy.context.scene
    lib.paint("open")
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.image_settings.file_format = "WEBP"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.quality = 90
    out = os.path.join(ASSETS, "cutouts")
    os.makedirs(out, exist_ok=True)
    meshes = [o for o in sc.objects if o.type in {"MESH", "CURVE", "FONT"}]
    dg = bpy.context.evaluated_depsgraph_get()   # curves only know their real size once evaluated
    box = {}
    for o in meshes:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        vs = [o.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
        lo = Vector([min(v[i] for v in vs) for i in range(3)]) if vs else o.matrix_world.translation
        hi = Vector([max(v[i] for v in vs) for i in range(3)]) if vs else o.matrix_world.translation
        box[o] = [lo, hi]
    for name, (az, el, keep) in CUTOUTS.items():
        mine = [o for o in meshes if o["grp"] == name and (keep is None or keep(box[o]))]
        for o in meshes:
            o.hide_render = o not in mine
        pts = [p for o in mine for p in box[o]]
        lo = Vector([min(p[i] for p in pts) for i in range(3)])
        hi = Vector([max(p[i] for p in pts) for i in range(3)])
        radius = (hi - lo).length / 2
        if sc.camera:
            bpy.data.objects.remove(sc.camera)
        lib.camera((lo + hi) / 2, radius / math.sin(math.radians(10)) * 1.02, az, el, fov=20)
        sc.render.filepath = os.path.join(out, name + ".webp")
        bpy.ops.render.render(write_still=True)
        print(f"[run] cutout {name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render")
    ap.add_argument("--bake", type=int)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--res", default="1280x960")
    ap.add_argument("--view")
    ap.add_argument("--paint", choices=("home", "open", "colour"), default="home")
    ap.add_argument("--blend", action="store_true")
    ap.add_argument("--cutouts", type=int, help="size in px of the collage cut-outs")
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    t0 = time.time()
    lib.reset()
    lib.PAINT = a.paint
    room.build()
    if a.view:   # AZIM,ELEV,DIST[,X,Y,Z] to look at something else than the room centre
        v = [float(x) for x in a.view.split(",")]
        bpy.data.objects.remove(bpy.context.scene.camera)
        lib.camera(v[3:6] if len(v) > 3 else room.TARGET, v[2], v[0], v[1])
    cycles(a.samples)
    print(f"[run] built in {time.time() - t0:.1f}s, {len(bpy.context.scene.objects)} objects")

    if a.render:
        render(a.render, [int(v) for v in a.res.split("x")])
    if a.cutouts:
        cutouts(a.cutouts)
    if a.bake or a.blend:
        objs = lib.finalize()
        tris = sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons)
        print(f"[run] {len(objs)} meshes: {sorted(o.name for o in objs)}, {tris} triangles")
        if a.blend:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "room.blend"))
    if a.bake:
        os.makedirs(STAGE, exist_ok=True)
        t1 = time.time()
        cull(objs)
        print(f"[run] visibility test took {time.time() - t1:.1f}s")
        unwrap(objs)
        for mode in ("home", "open"):
            t1 = time.time()
            bake(objs, a.bake, mode)
            print(f"[run] baked {mode} at {a.bake}px in {time.time() - t1:.1f}s")
        export(objs)
        for name in sorted(os.listdir(STAGE), key=lambda n: n == "room.json"):   # room.json last: it carries the version
            os.replace(os.path.join(STAGE, name), os.path.join(ASSETS, name))
    print(f"[run] done in {time.time() - t0:.1f}s")


main()
