"""
Procedural Blender build for the 30-second educational film
"How Children Remember What They Learn".

Run with Blender's Python module (bpy 5.x) or Blender itself:
    OUT_DIR=/path/to/out PREVIEW=1 python build_memory_scene.py      # low-res preview
    OUT_DIR=/path/to/out PREVIEW=0 python build_memory_scene.py      # 1920x1080 final

Timeline (30 fps, frames 1-900):
    Shot 1  classroom, over-the-shoulder push-in     frames   1-150
    Shot 2  head goes transparent, brain revealed     frames 150-300
    Shot 3  neural macro, working memory              frames 300-480
    Shot 4  neural macro, long-term memory            frames 480-690
    Shot 5  classroom, child solves independently     frames 690-900

Limitations (stated honestly in the production report):
    - No licensed human models are available offline, so the child and teacher
      are built from primitives (smooth-shaded, stylised figures, not photoreal).
    - The brain is an displaced ellipsoid with cloud-noise folds, not a
      segmented anatomical model.
"""
import bpy
import math
import os
import random
from mathutils import Vector

OUT = os.environ.get("OUT_DIR", os.path.abspath("out"))
PREVIEW = os.environ.get("PREVIEW", "1") == "1"
FRAME_RANGE = os.environ.get("FRAME_RANGE", "")  # e.g. "1-120"

random.seed(11)

# --------------------------------------------------------------------------
# Scene setup
# --------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30
sc.render.fps_base = 1.0
sc.frame_start = 1
sc.frame_end = 900
if FRAME_RANGE:
    a, b = FRAME_RANGE.split("-")
    sc.frame_start, sc.frame_end = int(a), int(b)

ENGINE = os.environ.get("ENGINE", "CYCLES")
sc.render.engine = "BLENDER_EEVEE" if ENGINE == "EEVEE" else "CYCLES"
if ENGINE != "EEVEE":
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
if PREVIEW:
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 16
else:
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 100
    sc.cycles.samples = int(os.environ.get("FINAL_SAMPLES", "8"))
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.filepath = os.path.join(OUT, "frames", "f_")
sc.view_settings.view_transform = "AgX"
if ENGINE == "EEVEE":
    sc.eevee.taa_render_samples = 32
    sc.eevee.use_shadows = True
    sc.eevee.use_raytracing = False

coll_class = bpy.data.collections.new("Classroom")
coll_macro = bpy.data.collections.new("NeuralMacro")
sc.collection.children.link(coll_class)
sc.collection.children.link(coll_macro)


def to(o, coll):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    coll.objects.link(o)
    return o


def mat(name, color, rough=0.5, metal=0.0, sss=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if sss > 0:
        b.inputs["Subsurface Weight"].default_value = sss
    return m, b


def emissive(name, color, base_color=(0.5, 0.4, 0.35), strength=0.0):
    m, b = mat(name, base_color, rough=0.4)
    b.inputs["Emission Color"].default_value = (*color, 1.0)
    b.inputs["Emission Strength"].default_value = strength
    return m, b


def key_emis(b, schedule):
    """schedule: list of (frame, strength) pairs."""
    for f, v in schedule:
        b.inputs["Emission Strength"].default_value = v
        b.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)


def sphere(name, loc, r, m, scale=(1, 1, 1), coll=None, segs=32):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=segs, ring_count=16)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return to(o, coll) if coll else o


def cylinder_between(name, a, b_, r, m, coll=None):
    a, b_ = Vector(a), Vector(b_)
    d = b_ - a
    L = d.length
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=L, location=(a + b_) / 2, vertices=24
    )
    o = bpy.context.object
    o.name = name
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return to(o, coll) if coll else o


def box(name, loc, size, m, coll=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = [s / 2 for s in size]
    o.data.materials.append(m)
    return to(o, coll) if coll else o


def empty(name, loc, coll=None):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    (coll or sc.collection).objects.link(o)
    return o


def catmull(pts, n=10):
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = [Vector(P[j]) for j in (i - 1, i, i + 1, i + 2)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                       + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append(q)
    out.append(Vector(pts[-1]))
    return out


def tube(name, pts, radius, m, coll):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.resolution_u = 4
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (q.x, q.y, q.z, 1.0)
    o = bpy.data.objects.new(name, cu)
    coll.objects.link(o)
    o.data.materials.append(m)
    return o


def lerp_frames(obj_data, attr, keys):
    """keys: list of (frame, value); keyframes an attribute of a data block."""
    for f, v in keys:
        setattr(obj_data, attr, v)
        obj_data.keyframe_insert(attr, frame=f)


def set_loc(o, keys):
    for f, v in keys:
        o.location = v
        o.keyframe_insert("location", frame=f)


def set_rot(o, keys):
    for f, v in keys:
        o.rotation_euler = v
        o.keyframe_insert("rotation_euler", frame=f)



def aim(cam, frame, loc, tgt):
    """Key a camera's location and rotation so it looks from loc at tgt (no constraints)."""
    d = Vector(tgt) - Vector(loc)
    cam.location = loc
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)

# --------------------------------------------------------------------------
# Classroom set
# --------------------------------------------------------------------------
C = coll_class
wood_m, _ = mat("Wood", (0.42, 0.27, 0.16), rough=0.55)
wall_m, _ = mat("WallCream", (0.86, 0.80, 0.70), rough=0.9)
board_m, _ = mat("Board", (0.93, 0.94, 0.92), rough=0.35)
desk_m, _ = mat("DeskTop", (0.62, 0.45, 0.30), rough=0.45)
metal_m, _ = mat("Metal", (0.2, 0.2, 0.22), rough=0.4, metal=0.8)
chair_m, _ = mat("Chair", (0.25, 0.42, 0.55), rough=0.5)
skin_m, _ = mat("Skin", (0.80, 0.56, 0.44), rough=0.5, sss=0.25)
shirt_m, _ = mat("ChildShirt", (0.30, 0.55, 0.62), rough=0.7)
teacher_shirt_m, _ = mat("TeacherShirt", (0.55, 0.25, 0.22), rough=0.7)
pants_m, _ = mat("Pants", (0.20, 0.22, 0.30), rough=0.7)
hair_m, _ = mat("Hair", (0.14, 0.09, 0.06), rough=0.6)
paper_m, _ = mat("Notebook", (0.96, 0.95, 0.90), rough=0.8)
marker_m, _ = mat("Ink", (0.05, 0.05, 0.25), rough=0.6)
def ghost_material(name, color, rough=0.45):
    gm = bpy.data.materials.new(name)
    gm.use_nodes = True
    nt = gm.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    pr = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    gval = nt.nodes.new("ShaderNodeValue")
    gval.outputs[0].default_value = 0.0
    pr.inputs["Base Color"].default_value = (*color, 1.0)
    pr.inputs["Roughness"].default_value = rough
    pr.inputs["Subsurface Weight"].default_value = 0.3
    nt.links.new(gval.outputs[0], mix.inputs[0])
    nt.links.new(pr.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return gm, gval


head_mix_m, _ghost = ghost_material("HeadGhost", (0.80, 0.56, 0.44))
hair_ghost_m, _ghost_hair = ghost_material("HairGhost", (0.14, 0.09, 0.06), rough=0.6)

# Floor, walls, ceiling
box("Floor", (0, 4, -0.02), (16, 18, 0.04), wood_m, C)
box("BackWall", (0, 8.6, 1.8), (16, 0.12, 3.6), wall_m, C)
box("LeftWall", (-7.0, 4, 1.8), (0.12, 18, 3.6), wall_m, C)
box("RightWall", (7.0, 4, 1.8), (0.12, 18, 3.6), wall_m, C)
box("Ceiling", (0, 4, 3.6), (16, 18, 0.1), wall_m, C)

# Whiteboard and equation
box("Whiteboard", (1.6, 8.5, 1.7), (3.4, 0.05, 1.3), board_m, C)
bpy.ops.object.text_add(location=(0.15, 8.45, 1.75))
eq = bpy.context.object
eq.name = "Equation"
eq.data.body = "2x + 4 = 10"
eq.data.size = 0.34
eq.data.align_x = "CENTER"
eq.rotation_euler = (math.pi / 2, 0, 0)  # reads correctly from the classroom
eq.data.materials.append(bpy.data.materials.new("Chalk"))
eq.data.materials[0].diffuse_color = (0.1, 0.45, 0.8, 1)
to(eq, C)

# Desk grid (the child's desk is at the front, centre)
desk_positions = [(-2.0, 2.4), (0.0, 2.4), (2.0, 2.4), (-2.0, 3.8), (0.0, 3.8), (2.0, 3.8)]
for i, (x, y) in enumerate(desk_positions):
    box(f"Desk{i}", (x, y, 0.72), (0.7, 0.5, 0.04), desk_m, C)
    for lx in (-0.3, 0.3):
        for ly in (-0.2, 0.2):
            box(f"DeskLeg{i}", (x + lx, y + ly, 0.36), (0.04, 0.04, 0.72), metal_m, C)
    box(f"Chair{i}", (x, y - 0.25, 0.45), (0.4, 0.4, 0.04), chair_m, C)
    box(f"ChairBack{i}", (x, y - 0.43, 0.80), (0.4, 0.04, 0.7), chair_m, C)

# Child's desk (front centre, where the camera sits behind the child)
box("ChildDesk", (0.0, 1.0, 0.72), (0.75, 0.5, 0.04), desk_m, C)
for lx in (-0.32, 0.32):
    for ly in (0.8, 1.2):
        box("ChildDeskLeg", (lx, ly, 0.36), (0.04, 0.04, 0.72), metal_m, C)
box("ChildChair", (0.0, 0.58, 0.45), (0.42, 0.42, 0.05), chair_m, C)
box("ChildChairBack", (0.0, 0.40, 0.84), (0.42, 0.05, 0.75), chair_m, C)
# Notebook on the desk
box("Notebook", (0.0, 1.02, 0.745), (0.34, 0.24, 0.01), paper_m, C)

# --- Child (seated, facing the board, +Y) ---
child_parts = []
child_parts.append(sphere("ChildHips", (0, 0.56, 0.58), 0.1, shirt_m, scale=(1.7, 1.2, 1.0), coll=C))
child_parts.append(sphere("ChildTorso", (0, 0.58, 0.98), 0.14, shirt_m, scale=(1.35, 0.95, 1.9), coll=C))
child_parts.append(cylinder_between("ChildNeck", (0, 0.60, 1.22), (0, 0.63, 1.34), 0.045, skin_m, C))
child_parts.append(sphere("ChildHairBack", (0, 0.585, 1.49), 0.112, hair_ghost_m, scale=(0.95, 1.0, 1.08), coll=C))
# Head (semi-transparent ghost material)
head = sphere("ChildHead", (0, 0.63, 1.47), 0.105, head_mix_m, scale=(0.92, 1.08, 1.12), coll=C)
for lx in (-0.12, 0.12):
    child_parts.append(cylinder_between(f"ChildThigh{lx}", (lx, 0.56, 0.52), (lx, 0.95, 0.50), 0.06, pants_m, C))
    child_parts.append(cylinder_between(f"ChildShin{lx}", (lx, 0.95, 0.50), (lx, 0.98, 0.10), 0.05, pants_m, C))
# Left arm resting on the desk
child_parts.append(cylinder_between("ChildLUpperArm", (-0.20, 0.60, 1.14), (-0.22, 0.80, 0.82), 0.045, shirt_m, C))
child_parts.append(cylinder_between("ChildLForearm", (-0.22, 0.80, 0.82), (-0.10, 0.98, 0.76), 0.04, shirt_m, C))
# Right (writing) arm: shoulder -> elbow (fixed), forearm rotates about the elbow
ELBOW = (0.20, 0.82, 0.82)
child_parts.append(cylinder_between("ChildRUpperArm", (0.20, 0.60, 1.14), ELBOW, 0.045, shirt_m, C))
elbow_pivot = empty("ChildElbowPivot", ELBOW, C)
fa = cylinder_between("ChildRForearm", ELBOW, (0.09, 1.00, 0.76), 0.04, shirt_m, C)
fa.parent = elbow_pivot
fa.matrix_parent_inverse = elbow_pivot.matrix_world.inverted()
hand = sphere("ChildRHand", (0.09, 1.00, 0.75), 0.04, skin_m, coll=C)
hand.parent = elbow_pivot
hand.matrix_parent_inverse = elbow_pivot.matrix_world.inverted()
for f in range(1, 901, 10):
    if f <= 150 or f >= 690:
        k = (f // 10) % 2
        elbow_pivot.rotation_euler = (0, 0, 0.06 * k)
        elbow_pivot.keyframe_insert("rotation_euler", frame=f)
    else:
        elbow_pivot.rotation_euler = (0, 0, 0)
        elbow_pivot.keyframe_insert("rotation_euler", frame=f)

# Brain (displaced ellipsoid with cloud-noise folds), inside the head
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1.0, location=(0, 0.63, 1.47))
brain = bpy.context.object
brain.name = "Brain"
brain_m, _brain_b = mat("BrainTissue", (0.86, 0.56, 0.58), rough=0.45, sss=0.35)
brain.data.materials.append(brain_m)
bpy.ops.object.shade_smooth()
tex = bpy.data.textures.new("Folds", type="CLOUDS")
tex.noise_scale = 0.22
disp = brain.modifiers.new("Folds", "DISPLACE")
disp.texture = tex
disp.strength = 0.22
disp.mid_level = 0.5
bpy.context.view_layer.objects.active = brain
bpy.ops.object.modifier_apply(modifier=disp.name)
brain.scale = (0.072, 0.088, 0.064)
to(brain, C)
cerebellum = sphere("Cerebellum", (0, 0.72, 1.32), 0.026, brain_m, scale=(1.4, 1.0, 0.8), coll=C)
stem = cylinder_between("BrainStem", (0, 0.68, 1.36), (0, 0.66, 1.30), 0.011, brain_m, C)

# Brain activity sparks (shot 2)
spark_m, spark_b = emissive("BrainSpark", (1.0, 0.82, 0.5), base_color=(0.8, 0.5, 0.5), strength=0.0)
rng = random.Random(3)
for i in range(12):
    p = (rng.uniform(-0.05, 0.05), 0.63 + rng.uniform(-0.06, 0.06), 1.47 + rng.uniform(-0.04, 0.04))
    sphere(f"Spark{i}", p, 0.0065, spark_m, coll=C, segs=12)
key_emis(spark_b, [(1, 0.0), (200, 0.0), (212, 4.5), (222, 0.0), (238, 0.0), (250, 4.5), (260, 0.0),
                   (274, 0.0), (284, 4.5), (294, 0.0), (300, 0.0)])

# Teacher, facing the board (back to the class), writing
T = (1.6, 7.0, 0)
teacher_parts = []
teacher_parts.append(cylinder_between("TeacherLegL", (T[0] - 0.12, T[1], 0.05), (T[0] - 0.12, T[1], 0.82), 0.07, pants_m, C))
teacher_parts.append(cylinder_between("TeacherLegR", (T[0] + 0.12, T[1], 0.05), (T[0] + 0.12, T[1], 0.82), 0.07, pants_m, C))
teacher_parts.append(sphere("TeacherTorso", (T[0], T[1], 1.15), 0.2, teacher_shirt_m, scale=(1.2, 0.85, 1.6), coll=C))
teacher_parts.append(sphere("TeacherHead", (T[0], T[1], 1.72), 0.115, skin_m, scale=(0.92, 1.0, 1.08), coll=C))
teacher_parts.append(sphere("TeacherHair", (T[0], T[1] + 0.01, 1.79), 0.12, hair_m, scale=(0.95, 1.0, 0.7), coll=C))
teacher_parts.append(cylinder_between("TeacherLArm", (T[0] - 0.24, T[1], 1.35), (T[0] - 0.24, T[1] + 0.05, 0.95), 0.05, teacher_shirt_m, C))
shoulder_pivot = empty("TeacherShoulderPivot", (T[0] + 0.24, T[1], 1.38), C)
arm = cylinder_between("TeacherRArm", (0, 0, 0), (0, 0.72, 0), 0.05, teacher_shirt_m, C)
arm.parent = shoulder_pivot
arm.matrix_parent_inverse = shoulder_pivot.matrix_world.inverted()
arm.location = (0, 0, 0)
for f in range(1, 901, 15):
    k = (f // 15) % 2
    shoulder_pivot.rotation_euler = (0.22 + 0.08 * k, 0, -0.10 + 0.05 * k)
    shoulder_pivot.keyframe_insert("rotation_euler", frame=f)

# Lights (classroom)
sun_d = bpy.data.lights.new("SunWindow", "SUN")
sun_d.energy = 2.2
sun_d.color = (1.0, 0.94, 0.84)
sun = bpy.data.objects.new("SunWindow", sun_d)
sc.collection.objects.link(sun)
sun.rotation_euler = (0.9, 0.0, -0.9)
area_w = bpy.data.lights.new("WindowLight", "AREA")
area_w.energy = 420
area_w.size = 3.2
area_w.size_y = 4.5
area_w.color = (1.0, 0.95, 0.88)
window = bpy.data.objects.new("WindowLight", area_w)
sc.collection.objects.link(window)
window.location = (-6.8, 2.5, 1.9)
window.rotation_euler = (0, -math.pi / 2, 0)
area_f = bpy.data.lights.new("FrontFill", "AREA")
area_f.energy = 120
area_f.size = 4.0
front = bpy.data.objects.new("FrontFill", area_f)
sc.collection.objects.link(front)
front.location = (0.0, -3.0, 2.6)
front.rotation_euler = (math.pi / 2, 0, 0)

# --------------------------------------------------------------------------
# Neural macro set (far away at x=30)
# --------------------------------------------------------------------------
M = coll_macro
MX = 30.0
soma_m, soma_b = mat("Soma", (0.82, 0.55, 0.52), rough=0.4, sss=0.2)
dend_m, _ = mat("Dendrite", (0.78, 0.50, 0.48), rough=0.5)
axA_m, axA_b = emissive("AxonA", (1.0, 0.78, 0.42), base_color=(0.8, 0.5, 0.45), strength=0.0)
axB_m, axB_b = emissive("AxonB", (1.0, 0.78, 0.42), base_color=(0.8, 0.5, 0.45), strength=0.0)
syn_m, syn_b = emissive("Synapse", (1.0, 0.85, 0.55), base_color=(0.9, 0.7, 0.6), strength=0.0)

S = {
    1: (MX - 0.80, -0.10, 0.50),
    2: (MX - 0.25, 0.25, 0.25),
    3: (MX + 0.35, -0.05, 0.45),
    4: (MX - 0.60, -0.55, 0.00),
    5: (MX + 0.00, -0.65, 0.20),
    6: (MX + 0.70, 0.45, 0.05),
}
soma_objs = {}
for k, p in S.items():
    soma_objs[k] = sphere(f"Soma{k}", p, 0.13, soma_m, coll=M, segs=48)
    # dendrite branches
    for j in range(6):
        d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 0.6))).normalized()
        end = Vector(p) + d * rng.uniform(0.18, 0.28)
        mid = Vector(p) + d * 0.1 + Vector((rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04)))
        tube(f"Dend{k}_{j}", [Vector(p), mid, end], 0.012, dend_m, M)
        # tube objects need linking after creation via tube()

PATH_A = [S[1], (MX - 0.52, 0.14, 0.52), S[2], (MX + 0.05, 0.16, 0.38), S[3]]
PATH_B = [S[4], (MX - 0.30, -0.66, 0.06), S[5], (MX + 0.36, -0.50, 0.16), S[6]]
PATH_FAINT = [S[2], (MX - 0.10, -0.24, 0.18), S[5]]
curveA = tube("AxonPathA", catmull(PATH_A), 0.012, axA_m, M)
curveB = tube("AxonPathB", catmull(PATH_B), 0.012, axB_m, M)
curveF = tube("FaintLink", catmull(PATH_FAINT), 0.006, dend_m, M)
curveB.data.bevel_depth = 0.009
curveB.data.keyframe_insert("bevel_depth", frame=1)

# Synapses at contact points
syn_pos_A = [(MX - 0.52, 0.14, 0.52), (MX + 0.05, 0.16, 0.38)]
syn_pos_B = [(MX - 0.30, -0.66, 0.06), (MX + 0.36, -0.50, 0.16)]
syn_A = [sphere(f"SynA{i}", p, 0.024, syn_m, coll=M, segs=24) for i, p in enumerate(syn_pos_A)]
syn_B = [sphere(f"SynB{i}", p, 0.024, syn_m, coll=M, segs=24) for i, p in enumerate(syn_pos_B)]

# Macro lighting (only lights the neural set)
lm = bpy.data.lights.new("MacroKey", "AREA")
lm.energy = 500
lm.size = 3.0
lm_o = bpy.data.objects.new("MacroKey", lm)
sc.collection.objects.link(lm_o)
lm_o.location = (MX, -1.6, 1.8)
lm_o.rotation_euler = (0.5, 0, 0)
to(lm_o, M)
lr = bpy.data.lights.new("MacroRim", "POINT")
lr.energy = 25
lr.color = (1.0, 0.7, 0.6)
lr_o = bpy.data.objects.new("MacroRim", lr)
sc.collection.objects.link(lr_o)
lr_o.location = (MX + 0.8, 0.9, 0.9)
to(lr_o, M)

# Working memory vs long-term memory activation schedules
# Path A: working-memory flashes 330/360/390, then long-term flashes every 24 frames 480-680
A_sched = [(1, 0.0), (326, 0.0), (330, 5.0), (340, 0.0), (356, 0.0), (360, 5.0), (370, 0.0),
           (386, 0.0), (390, 5.0), (400, 0.0), (420, 0.0)]
for f in range(480, 690, 24):
    A_sched += [(f, 0.6), (f + 6, 9.0), (f + 16, 0.6)]
A_sched += [(690, 0.6)]
key_emis(axA_b, A_sched)
key_emis(syn_b, [(1, 0.0), (326, 0.0), (330, 4.0), (350, 0.0), (480, 0.0), (500, 3.0), (520, 0.8),
                 (560, 4.0), (600, 1.2), (640, 4.5), (690, 1.2)])
# Path B: one working-memory flash, then fades out without reinforcement
B_sched = [(1, 0.0), (336, 0.0), (340, 4.0), (352, 0.0), (480, 0.0), (500, 0.0), (520, 0.0)]
key_emis(axB_b, B_sched)
key_emis(syn_b, [])  # keeps synapse track; B synapses use syn_b too (see below)
# Path A's connector axon brightness is shared with syn_b; the B synapses get their own material
for o in syn_B:
    o.data.materials[0] = bpy.data.materials.new("SynapseB")
    o.data.materials[0].use_nodes = True
    bb = o.data.materials[0].node_tree.nodes["Principled BSDF"]
    bb.inputs["Base Color"].default_value = (0.9, 0.7, 0.6, 1)
    bb.inputs["Emission Color"].default_value = (1.0, 0.85, 0.55, 1)
    key_emis(bb, [(1, 0.0), (336, 0.0), (340, 3.0), (352, 0.0), (400, 0.0), (480, 0.0)])

# Bevel: path A thickens with repetition, path B thins without it
curveA.data.bevel_depth = 0.005
curveA.data.keyframe_insert("bevel_depth", frame=1)
curveA.data.bevel_depth = 0.006
curveA.data.keyframe_insert("bevel_depth", frame=330)
curveA.data.bevel_depth = 0.006
curveA.data.keyframe_insert("bevel_depth", frame=470)
curveA.data.bevel_depth = 0.016
curveA.data.keyframe_insert("bevel_depth", frame=690)
curveB.data.bevel_depth = 0.009
curveB.data.keyframe_insert("bevel_depth", frame=470)
curveB.data.bevel_depth = 0.003
curveB.data.keyframe_insert("bevel_depth", frame=690)
# Synapses grow with reinforcement
for o in syn_A:
    o.scale = (1, 1, 1)
    o.keyframe_insert("scale", frame=470)
    o.scale = (1.8, 1.8, 1.8)
    o.keyframe_insert("scale", frame=690)
for o in syn_B:
    o.scale = (1, 1, 1)
    o.keyframe_insert("scale", frame=470)
    o.scale = (0.5, 0.5, 0.5)
    o.keyframe_insert("scale", frame=690)

# Macro camera (dollies slowly along +X during the neural sequence)
cam_m_d = bpy.data.cameras.new("CamMacro")
cam_m_d.lens = 50
cam_m_d.dof.use_dof = False  # depth of field left off: it blanked macro frames in this build
cam_m = bpy.data.objects.new("CamMacro", cam_m_d)
sc.collection.objects.link(cam_m)
to(cam_m, M)
aim(cam_m, 300, (MX - 0.05, -2.2, 0.85), (MX - 0.10, 0.0, 0.25))
aim(cam_m, 690, (MX + 0.25, -2.2, 0.85), (MX + 0.10, 0.0, 0.25))
cam_m_d.dof.focus_object = None

# Macro labels, parented to the macro camera
def label(text, frames_on):
    cu = bpy.data.curves.new("Label_" + text.replace(" ", "_"), "FONT")
    cu.body = text
    cu.size = 0.055 * 0.4 / 1.7  # same framing, but in front of every neuron
    o = bpy.data.objects.new("Label_" + text.replace(" ", "_"), cu)
    sc.collection.objects.link(o)
    o.parent = cam_m
    o.location = (-0.099, 0.064, -0.4)  # top-left clear band, in front of every neuron
    m, b = mat("LabelInk", (0.98, 0.94, 0.88), rough=0.4)
    b.inputs["Emission Color"].default_value = (1, 0.95, 0.9, 1)
    b.inputs["Emission Strength"].default_value = 0.6
    o.data.materials.append(m)
    # visible only in its window
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=1)
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=frames_on[0])
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=frames_on[1])
    return o

label_wm = label("WORKING MEMORY", (310, 470))
label_ltm = label("LONG-TERM MEMORY", (490, 680))

# --------------------------------------------------------------------------
# Classroom camera (shots 1, 2 and 5)
# --------------------------------------------------------------------------
cam_c_d = bpy.data.cameras.new("CamClass")
cam_c_d.lens = 35
cam_c_d.dof.use_dof = True
cam_c_d.dof.aperture_fstop = 2.2
cam_c_d.dof.focus_object = head
cam_c = bpy.data.objects.new("CamClass", cam_c_d)
sc.collection.objects.link(cam_c)
# Shot 1: over-the-shoulder, slow push toward the child (1-150)
aim(cam_c, 1, (0.20, -1.35, 1.42), (0.05, 3.2, 1.25))
aim(cam_c, 150, (0.16, -0.95, 1.40), (0.05, 3.0, 1.25))
# Shot 2: move toward the back of the head, looking at the brain (150-300)
aim(cam_c, 300, (0.12, -0.33, 1.62), (0.0, 0.63, 1.45))
# Shot 5: pull back into the classroom (690-900)
aim(cam_c, 690, (0.12, -0.33, 1.62), (0.0, 0.63, 1.45))
aim(cam_c, 900, (0.30, -2.4, 1.75), (0.6, 4.2, 1.2))

# Head ghosting (shot 2): fully opaque until 170, transparent by 215, opaque again by 700
_ghost.outputs[0].default_value = 0.0
_ghost.outputs[0].keyframe_insert("default_value", frame=1)
_ghost.outputs[0].default_value = 0.0
_ghost.outputs[0].keyframe_insert("default_value", frame=170)
_ghost.outputs[0].default_value = 0.82
_ghost.outputs[0].keyframe_insert("default_value", frame=215)
_ghost.outputs[0].default_value = 0.82
_ghost.outputs[0].keyframe_insert("default_value", frame=300)
_ghost.outputs[0].default_value = 0.82
_ghost.outputs[0].keyframe_insert("default_value", frame=690)
_ghost.outputs[0].default_value = 0.0
_ghost.outputs[0].keyframe_insert("default_value", frame=720)
for _f, _v in [(1, 0.0), (170, 0.0), (215, 0.82), (300, 0.82), (690, 0.82), (720, 0.0)]:
    _ghost_hair.outputs[0].default_value = _v
    _ghost_hair.outputs[0].keyframe_insert("default_value", frame=_f)

# Sun and classroom lights only affect the classroom set (light linking)
sun.light_linking.receiver_collection = C
window.light_linking.receiver_collection = C
front.light_linking.receiver_collection = C
lm_o.light_linking.receiver_collection = M
lr_o.light_linking.receiver_collection = M

# Macro set: classroom lights turned off while the neural set is on screen
for o in (sun, window, front):
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=1)

# World: warm classroom ambience, dark neural set
world = bpy.data.worlds.new("World")
sc.world = world
world.use_nodes = True
wbg = world.node_tree.nodes["Background"]
wbg.inputs["Color"].default_value = (0.55, 0.5, 0.45, 1.0)
wbg.inputs["Strength"].default_value = 0.35
wbg.inputs["Strength"].keyframe_insert("default_value", frame=1)
wbg.inputs["Strength"].default_value = 0.15
wbg.inputs["Strength"].keyframe_insert("default_value", frame=300)
wbg.inputs["Strength"].default_value = 0.15
wbg.inputs["Strength"].keyframe_insert("default_value", frame=690)
wbg.inputs["Strength"].default_value = 0.35
wbg.inputs["Strength"].keyframe_insert("default_value", frame=720)

# Camera switching on the timeline
sc.timeline_markers.new("CLASSROOM", frame=1).camera = cam_c
sc.timeline_markers.new("NEURAL_MACRO", frame=300).camera = cam_m
sc.timeline_markers.new("CLASSROOM_RETURN", frame=690).camera = cam_c
sc.camera = cam_c


def _switch_camera(scene, *_):
    """Use the neural macro camera for frames 300-689, the classroom camera otherwise."""
    scene.camera = cam_m if 300 <= scene.frame_current < 690 else cam_c


bpy.app.handlers.frame_change_pre.append(_switch_camera)

# Make sure the classroom and macro sets are visible in their own shots only:
# hide the neural set in classroom frames and the classroom in macro frames.
for o in list(coll_macro.objects):
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=1)
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=300)
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=690)
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=692)
for o in list(coll_class.objects):
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=1)
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=300)
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=690)
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=692)

if __name__ == "__main__":
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "memory_scene.blend"))
    print("Scene built. Frames", sc.frame_start, "-", sc.frame_end)
    bpy.ops.render.render(animation=True)
