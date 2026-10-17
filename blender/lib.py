"""Helpers to build the room procedurally in Blender (run headless, see run.py).

Everything is in metres, Z up. Objects are tagged with a group id ("room" for the
static shell, or the id of a clickable thing); finalize() joins one mesh per group.
"""
import math
from contextlib import contextmanager

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

# What is white, like a card-stock maquette: "home" the clickable things (the room is in colour),
# "open" the room (the things are in colour), "colour" nothing. paint() switches it after the build.
PAINT = "home"

UV_SCALE = {}  # group id -> texel density multiplier in the baked atlas (default 1)
DECOR = {"mirrors", "glow", "secret"}  # part of the room (painted like it) but exported as their own mesh

_mats = {}
_grp = "room"
_xf = Matrix.Identity(4)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


# ---------------------------------------------------------------- materials
def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rgb(hexcol):
    h = hexcol.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def clay_of(rgb, base=0.46):
    """Light grey that keeps a hint of the original value (dark wood stays a bit darker)."""
    g = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    v = base + (0.88 - base) * g
    return [v, v * 0.985, v * 0.955]   # a touch warm, like card stock


def mat(hexcol, rough=0.75, emit=0.0, metal=0.0, keep=False):
    """keep=True: always in colour, whatever is white (lamps, candles)."""
    kind = "keep" if keep else ("room" if _grp == "room" or _grp in DECOR else "thing")
    key = (hexcol, rough, emit, metal, kind)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(hexcol)
    m.use_nodes = True
    m["rgb"], m["kind"], m["metal"] = _rgb(hexcol), kind, metal
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    b.inputs["Emission Strength"].default_value = emit
    _paint(m, PAINT)
    _mats[key] = m
    return m


def optical_white(rgb):
    """Bright, slightly cool white for the clickable things: the warm evening light would turn a neutral
    white into cream. A hint of the original value stays, so dark parts still read as parts."""
    g = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    v = 0.9 + 0.1 * g
    return [v * 0.93, v * 0.96, v]


def _paint(m, mode):
    rgb = list(m["rgb"])
    white = m["kind"] == {"home": "thing", "open": "room"}.get(mode)
    if white:
        rgb = optical_white(rgb) if m["kind"] == "thing" else clay_of(rgb)
    col = [_lin(c) for c in rgb] + [1.0]
    b = m.node_tree.nodes["Principled BSDF"]
    # the white room is matte, like card stock: a metal there (the mirror tiles) would bake as a dark
    # reflection, and the page shows those tiles when their glints fade out
    b.inputs["Metallic"].default_value = 0.0 if white and m["kind"] == "room" else m["metal"]
    b.inputs["Base Color"].default_value = col
    b.inputs["Emission Color"].default_value = col


def paint(mode):
    """Repaint every material for `mode` (see PAINT)."""
    global PAINT
    PAINT = mode
    for m in _mats.values():
        _paint(m, mode)


# ---------------------------------------------------------------- grouping
@contextmanager
def group(grp=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, uv=None):
    """Everything created inside is tagged `grp` and placed in this local frame (rot in degrees)."""
    global _grp, _xf
    old = (_grp, _xf)
    if grp:
        _grp = grp
        if uv:
            UV_SCALE[grp] = uv
    _xf = _xf @ Matrix.LocRotScale(Vector(loc), Euler([math.radians(a) for a in rot]), Vector((scale,) * 3))
    try:
        yield
    finally:
        _grp, _xf = old


def _add(name, data, loc=(0, 0, 0), rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    o["grp"] = _grp
    o.matrix_world = _xf @ Matrix.LocRotScale(Vector(loc), Euler([math.radians(a) for a in rot]), None)
    return o


def _finish(o, col, bevel=0.0, seg=2, sharp=35, **mk):
    me = o.data
    if col is not None:
        me.materials.append(mat(col, **mk))
    if o.type == "MESH":
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp))
        if bevel > 0:
            b = o.modifiers.new("bevel", "BEVEL")
            b.width, b.segments = bevel, seg
            b.limit_method, b.angle_limit = "ANGLE", math.radians(sharp)
            w = o.modifiers.new("wn", "WEIGHTED_NORMAL")
            w.keep_sharp = True
    return o


# ---------------------------------------------------------------- primitives
def box(x, y, z, sx, sy, sz, col, bevel=0.008, seg=2, rot=(0, 0, 0), name="box", **mk):
    """Box from its min corner and size. `rot` (degrees) turns it around its centre."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = _add(name, me, (x + sx / 2, y + sy / 2, z + sz / 2), rot)
    return _finish(o, col, bevel, seg, **mk)


def cyl(cx, cy, z, r, h, col, r2=None, axis="Z", segs=32, bevel=0.0, seg=2, rot=None, name="cyl", **mk):
    """Cylinder/cone standing on (cx, cy, z) along `axis`, radius r at the base and r2 at the top."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                          radius1=r, radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.translate(bm, vec=(0, 0, h / 2), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    r_ = rot if rot is not None else {"Z": (0, 0, 0), "X": (0, 90, 0), "Y": (-90, 0, 0)}[axis]
    o = _add(name, me, (cx, cy, z), r_)
    return _finish(o, col, bevel, seg, **mk)


def sphere(cx, cy, cz, r, col, scale=(1, 1, 1), segs=24, rot=(0, 0, 0), name="sphere", **mk):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=r)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return _finish(_add(name, me, (cx, cy, cz), rot), col, sharp=80, **mk)


def torus(cx, cy, cz, R, r, col, rot=(0, 0, 0), segs=48, name="torus", **mk):
    """Ring lying in the XY plane (before `rot`)."""
    bm = bmesh.new()
    n, m_ = segs, 10
    rings = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ring = []
        for j in range(m_):
            b = 2 * math.pi * j / m_
            d = R + r * math.cos(b)
            ring.append(bm.verts.new((d * math.cos(a), d * math.sin(a), r * math.sin(b))))
        rings.append(ring)
    for i in range(n):
        for j in range(m_):
            bm.faces.new((rings[i][j], rings[(i + 1) % n][j], rings[(i + 1) % n][(j + 1) % m_], rings[i][(j + 1) % m_]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return _finish(_add(name, me, (cx, cy, cz), rot), col, sharp=80, **mk)


def tube(points, r, col, closed=False, smooth=False, res=6, name="tube", **mk):
    """Round tube through 3D points (straight segments, or a smooth bezier with smooth=True)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = r, res // 2, True
    cu.resolution_u = 10
    if smooth:
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(points) - 1)
        for bp, p in zip(sp.bezier_points, points):
            bp.co = p
            bp.handle_left_type = bp.handle_right_type = "AUTO"
    else:
        sp = cu.splines.new("POLY")
        sp.points.add(len(points) - 1)
        for sp_p, p in zip(sp.points, points):
            sp_p.co = (*p, 1)
    sp.use_cyclic_u = closed
    o = _add(name, cu)
    cu.materials.append(mat(col, **mk))
    return o


def tiles(origin, du, dv, nu, nv, colour, name="tiles", **mk):
    """A flat grid of nu x nv tiles at origin + i*du + j*dv (one mesh, one face per tile, so it unwraps
    as a single island). colour(i, j) gives each tile's colour, or None to leave a hole.
    The faces point along du x dv."""
    bm = bmesh.new()
    O, U, V = Vector(origin), Vector(du), Vector(dv)
    verts, slots = {}, {}
    def vert(i, j):
        if (i, j) not in verts:
            verts[(i, j)] = bm.verts.new(O + U * i + V * j)
        return verts[(i, j)]
    for i in range(nu):
        for j in range(nv):
            c = colour(i, j)
            if c is None:
                continue
            f = bm.faces.new((vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1)))
            f.material_index = slots.setdefault(c, len(slots))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = _add(name, me)
    for c in slots:
        me.materials.append(mat(c, **mk))
    return o


def prism(outline, z, h, col, bevel=0.0, seg=2, loc=(0, 0, 0), rot=(0, 0, 0), sharp=35, name="prism", **mk):
    """Flat 2D outline (list of (x, y)) extruded upward by h, starting at height z."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, z)) for x, y in outline]
    f = bm.faces.new(vs)
    if f.normal.z > 0:
        f.normal_flip()
    top = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, 0, h), verts=[g for g in top["geom"] if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return _finish(_add(name, me, loc, rot), col, bevel, seg, sharp=sharp, **mk)


def text(s, x, y, z, size, col, rot=(90, 0, 0), depth=0.0015, align="LEFT", shear=0.0, font=None, name="text", **mk):
    """Flat lettering. Default orientation stands on the back wall facing the room;
    rot=(90, 0, 90) puts it on the left wall. `font` is a path to a .ttf (Blender's own font otherwise)."""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body, cu.size, cu.extrude, cu.align_x, cu.shear = s, size, depth, align, shear
    if font:
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.resolution_u = 2
    o = _add(name, cu, (x, y, z), rot)
    cu.materials.append(mat(col, **mk))
    return o


def spline(pts, n=8, closed=False):
    """Catmull-Rom curve through 2D or 3D points, n steps per span."""
    P = [Vector(p) for p in pts]
    m = len(P)
    get = (lambda i: P[i % m]) if closed else (lambda i: P[min(max(i, 0), m - 1)])
    out = []
    for i in range(m if closed else m - 1):
        p0, p1, p2, p3 = get(i - 1), get(i), get(i + 1), get(i + 2)
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed:
        out.append(P[-1])
    return [tuple(v) for v in out]


def loft(sections, col, closed_ends=True, loc=(0, 0, 0), rot=(0, 0, 0), name="loft", sharp=60, **mk):
    """Skin a list of cross-sections (each a list of 3D points, same count) into a closed surface."""
    bm = bmesh.new()
    rings = [[bm.verts.new(p) for p in sec] for sec in sections]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    if closed_ends:
        bm.faces.new(reversed(rings[0]))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return _finish(_add(name, me, loc, rot), col, sharp=sharp, **mk)


def drape(x0, y0, x1, y1, z, col, hang=(0.2, 0.2, 0.2, 0.2), r=0.05, res=0.035, wave=0.004, thick=0.03,
          name="drape", **mk):
    """A cloth lying flat on the rectangle [x0,x1] x [y0,y1] at height z, rolling over the edges
    (radius r) and hanging down. hang = cloth length past the (x0, x1, y0, y1) edges."""
    hx0, hx1, hy0, hy1 = hang
    ax, bx, ay, by = x0 - hx0, x1 + hx1, y0 - hy0, y1 + hy1
    nx, ny = max(2, round((bx - ax) / res)), max(2, round((by - ay) / res))
    arc = math.pi * r / 2
    bm = bmesh.new()
    grid = []
    for i in range(nx + 1):
        row = []
        for j in range(ny + 1):
            px, py = ax + (bx - ax) * i / nx, ay + (by - ay) * j / ny
            qx, qy = min(max(px, x0), x1), min(max(py, y0), y1)
            dx, dy = px - qx, py - qy
            d = math.hypot(dx, dy)
            # gentle wrinkles, fading out where the cloth falls
            w = wave * (math.sin(px * 23 + py * 7) * 0.6 + math.sin(py * 31 - px * 5) * 0.4) * max(0.0, 1 - d / arc)
            if d < 1e-9:
                co = (px, py, z + w)
            else:
                h, v = (r * math.sin(d / r), r * (1 - math.cos(d / r))) if d <= arc else (r, r + d - arc)
                co = (qx + dx / d * h, qy + dy / d * h, z - v + w)
            row.append(bm.verts.new(co))
        grid.append(row)
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = _add(name, me)
    _finish(o, col, sharp=89, **mk)
    s = o.modifiers.new("thick", "SOLIDIFY")
    s.thickness, s.offset = thick, 1.0
    return o


def soft(o, r=0.05, levels=2):
    """Turn a boxy mesh into a pillowy one: edges rounded by r, then subdivided."""
    for m in list(o.modifiers):
        o.modifiers.remove(m)
    for p in o.data.polygons:
        p.use_smooth = True
    for e in o.data.edges:
        e.use_edge_sharp = False
    b = o.modifiers.new("bevel", "BEVEL")
    b.width, b.segments, b.limit_method = r, 1, "NONE"
    s = o.modifiers.new("subd", "SUBSURF")
    s.levels = s.render_levels = levels
    return o


# ---------------------------------------------------------------- lights / camera
def sun(direction, strength, col=(1, 1, 1), angle=6):
    """Parallel light travelling along `direction`."""
    d = bpy.data.lights.new("sun", "SUN")
    d.energy, d.color, d.angle = strength, col, math.radians(angle)
    o = bpy.data.objects.new("sun", d)
    bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return o


def lamp(loc, power, col=(1, 1, 1), radius=0.05):
    """Point light, e.g. the bulb inside a lampshade."""
    d = bpy.data.lights.new("lamp", "POINT")
    d.energy, d.color, d.shadow_soft_size = power, col, radius
    o = bpy.data.objects.new("lamp", d)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return o


def area(loc, target, size, power, col=(1, 1, 1)):
    d = bpy.data.lights.new("area", "AREA")
    d.energy, d.color, d.size = power, col, size
    o = bpy.data.objects.new("area", d)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def world(light_hex, strength, bg_hex):
    """Uniform sky light; the camera sees `bg_hex` instead (same colour as the web page)."""
    w = bpy.data.worlds.new("world")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    mix = nt.nodes.new("ShaderNodeMixShader")
    lp = nt.nodes.new("ShaderNodeLightPath")
    a = nt.nodes.new("ShaderNodeBackground")
    b = nt.nodes.new("ShaderNodeBackground")
    a.inputs[0].default_value = [_lin(c) for c in _rgb(light_hex)] + [1]
    a.inputs[1].default_value = strength
    b.inputs[0].default_value = [_lin(c) for c in _rgb(bg_hex)] + [1]
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(a.outputs[0], mix.inputs[1])
    nt.links.new(b.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])


def camera(target, dist, azim, elev, fov=22):
    """Same convention as the web viewer: orbit around `target`, angles in degrees."""
    d = bpy.data.cameras.new("cam")
    d.sensor_fit, d.angle = "VERTICAL", math.radians(fov)
    o = bpy.data.objects.new("cam", d)
    bpy.context.scene.collection.objects.link(o)
    a, e = math.radians(azim), math.radians(elev)
    t = Vector(target)
    o.location = t + dist * Vector((math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)))
    o.rotation_euler = (t - o.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = o
    return o


# ---------------------------------------------------------------- finalize
def finalize():
    """Apply modifiers, bake transforms into the meshes and join one mesh per group."""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for o in list(sc.objects):
        if o.type not in {"MESH", "CURVE", "FONT"}:
            continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        me.transform(o.matrix_world)
        n = bpy.data.objects.new(o.name, me)
        sc.collection.objects.link(n)
        groups.setdefault(o["grp"], []).append(n)
        bpy.data.objects.remove(o)
    out = []
    for grp, objs in groups.items():
        if len(objs) > 1:
            with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
                bpy.ops.object.join()
        objs[0].name = objs[0].data.name = grp
        out.append(objs[0])
    return out
