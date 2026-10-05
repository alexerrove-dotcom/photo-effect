import bpy, os, math
from mathutils import Vector

ROOT=os.environ.get("ASSET_ROOT","/tmp/catdogs_assets")
OUT=os.environ.get("ASSET_OUT","catdogs/generated")
os.makedirs(OUT,exist_ok=True)

SOLDIER=os.path.join(ROOT,"soldier.glb")
CAT=os.path.join(ROOT,"cat.glb")
DOG=os.path.join(ROOT,"dog.glb")

CAT_COLORS=[
    (0.045,0.22,0.48,1),(0.035,0.12,0.25,1),(0.10,0.32,0.56,1),(0.10,0.24,0.34,1),(0.04,0.16,0.28,1)
]
DOG_COLORS=[
    (0.42,0.10,0.07,1),(0.24,0.08,0.06,1),(0.50,0.17,0.10,1),(0.30,0.12,0.07,1),(0.18,0.07,0.06,1)
]
WEAPONS=["AK","SMG","Shotgun","Sniper","Pistol"]

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def mesh_bounds(obj):
    pts=[obj.matrix_world@v.co for v in obj.data.vertices]
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mn,mx,mx-mn,(mn+mx)*.5

def scene_bounds(exclude_names=()):
    pts=[]
    for o in bpy.context.scene.objects:
        if o.type=="MESH" and o.name not in exclude_names and not o.hide_render:
            pts += [o.matrix_world@v.co for v in o.data.vertices]
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mn,mx,mx-mn,(mn+mx)*.5

def clone_and_tint_materials(team,variant):
    base=CAT_COLORS[variant] if team=="cat" else DOG_COLORS[variant]
    for o in bpy.context.scene.objects:
        if o.type!="MESH": continue
        for slot in o.material_slots:
            m=slot.material
            if not m: continue
            nm=m.copy()
            slot.material=nm
            n=(m.name or "").lower()
            if "character_main" in n:
                nm.diffuse_color=base
                if nm.use_nodes and nm.node_tree:
                    bs=nm.node_tree.nodes.get("Principled BSDF")
                    if bs:
                        bs.inputs["Base Color"].default_value=base
                        bs.inputs["Roughness"].default_value=.58
            elif "pants" in n:
                c=(.025,.035,.045,1) if team=="cat" else (.045,.025,.02,1)
                nm.diffuse_color=c
                if nm.use_nodes and nm.node_tree:
                    bs=nm.node_tree.nodes.get("Principled BSDF")
                    if bs: bs.inputs["Base Color"].default_value=c
            elif "grey" in n or "black" in n:
                if nm.use_nodes and nm.node_tree:
                    bs=nm.node_tree.nodes.get("Principled BSDF")
                    if bs:
                        bs.inputs["Roughness"].default_value=.36
                        bs.inputs["Metallic"].default_value=.22

def extract_animal_head(path, team, target_center, target_dims, soldier_arm):
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new=[o for o in bpy.context.scene.objects if o not in before]
    animal_mesh=max((o for o in new if o.type=="MESH" and o.name!="Icosphere"),key=lambda o:len(o.data.vertices))
    # Apply rest-pose armature deformation to make a clean static head mesh.
    bpy.context.view_layer.objects.active=animal_mesh
    animal_mesh.select_set(True)
    for mod in list(animal_mesh.modifiers):
        if mod.type=="ARMATURE":
            try: bpy.ops.object.modifier_apply(modifier=mod.name)
            except: pass
    # Keep upper/head geometry. Both source models use Z-up after glTF import.
    cutoff=.54 if team=="cat" else .90
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for v in animal_mesh.data.vertices:
        wz=(animal_mesh.matrix_world@v.co).z
        v.select = wz >= cutoff
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="INVERT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    head=animal_mesh
    head.name=("CatHead" if team=="cat" else "DogHead")
    # Detach while preserving world transform.
    mw=head.matrix_world.copy()
    head.parent=None
    head.matrix_world=mw
    # Delete the animal rig and helper geometry.
    for o in list(new):
        if o is head: continue
        bpy.data.objects.remove(o,do_unlink=True)
    # Fit to soldier head dimensions.
    mn,mx,dim,cen=mesh_bounds(head)
    desired=Vector((target_dims.x*1.08,target_dims.y*(1.15 if team=="dog" else 1.04),target_dims.z*1.08))
    factors=Vector((desired.x/max(dim.x,.001),desired.y/max(dim.y,.001),desired.z/max(dim.z,.001)))
    head.scale.x*=factors.x; head.scale.y*=factors.y; head.scale.z*=factors.z
    bpy.context.view_layer.update()
    _,_,_,cen2=mesh_bounds(head)
    head.location += target_center-cen2
    bpy.context.view_layer.update()
    # Slightly push canine muzzle forward (-Y), cat only minimally.
    if team=="dog": head.location.y-=.06
    else: head.location.y-=.015
    bpy.context.view_layer.update()
    # Parent to soldier's head bone without changing current world placement.
    mw=head.matrix_world.copy()
    head.parent=soldier_arm
    head.parent_type="BONE"
    head.parent_bone="Head"
    head.matrix_world=mw
    return head

def add_uv(name,loc,scale,color,parent=None,bone=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    m=bpy.data.materials.new(name+"Mat"); m.diffuse_color=color
    m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    if bs:
        bs.inputs["Base Color"].default_value=color
        bs.inputs["Roughness"].default_value=.32
        bs.inputs["Metallic"].default_value=.30 if color[0]<.2 else .0
    o.data.materials.append(m)
    if parent:
        mw=o.matrix_world.copy(); o.parent=parent; o.parent_type="BONE"; o.parent_bone=bone; o.matrix_world=mw
    return o

def add_headset_and_goggles(head,arm,team):
    mn,mx,d,c=mesh_bounds(head)
    # Face points toward -Y for these source assets.
    glass=(.02,.07,.10,1)
    # goggles
    for sx in (-1,1):
        add_uv("Goggle",Vector((c.x+sx*d.x*.20,mn.y-.015,c.z+d.z*.08)),
               Vector((d.x*.16,d.y*.055,d.z*.12)),glass,arm,"Head")
    # headset cups
    for sx in (-1,1):
        add_uv("Headset",Vector((c.x+sx*d.x*.53,c.y,c.z+d.z*.05)),
               Vector((d.x*.10,d.y*.13,d.z*.18)),(.025,.03,.035,1),arm,"Head")
    # helmet shell: dark ellipsoid set above skull; deliberately leaves face/muzzle visible.
    add_uv("Helmet",Vector((c.x,c.y+d.y*.08,c.z+d.z*.34)),
           Vector((d.x*.54,d.y*.43,d.z*.30)),(.035,.045,.05,1),arm,"Head")

def add_tail(arm,head,team):
    # Simple curved tactical silhouette, bone-parented at hips.
    curve=bpy.data.curves.new(team+"Tail","CURVE"); curve.dimensions="3D"; curve.bevel_depth=.055 if team=="cat" else .07; curve.bevel_resolution=3
    spl=curve.splines.new("BEZIER"); spl.bezier_points.add(3)
    pts=[Vector((0,.16,.58)),Vector((0,.38,.53)),Vector((.12,.50,.82)),Vector((.20,.46,1.03))]
    for p,co in zip(spl.bezier_points,pts):
        p.co=co; p.handle_left_type="AUTO"; p.handle_right_type="AUTO"
    o=bpy.data.objects.new(team+"Tail",curve); bpy.context.collection.objects.link(o)
    m=bpy.data.materials.new(team+"TailMat")
    m.diffuse_color=(.30,.28,.25,1) if team=="cat" else (.34,.21,.12,1)
    curve.materials.append(m)
    mw=o.matrix_world.copy(); o.parent=arm; o.parent_type="BONE"; o.parent_bone="Hips"; o.matrix_world=mw

def prepare_soldier(team,variant):
    bpy.ops.import_scene.gltf(filepath=SOLDIER)
    arm=next(o for o in bpy.context.scene.objects if o.type=="ARMATURE")
    # Remove helper.
    for o in list(bpy.context.scene.objects):
        if o.name.startswith("Icosphere"): bpy.data.objects.remove(o,do_unlink=True)
    # Capture the original head target before removing it.
    human_head=next(o for o in bpy.context.scene.objects if o.type=="MESH" and o.name=="Head")
    hmn,hmx,hdim,hcen=mesh_bounds(human_head)
    bpy.data.objects.remove(human_head,do_unlink=True)
    # Keep one real weapon per character.
    for w in ["AK","SMG","Shotgun","Sniper","Pistol","Revolver","Revolver_Small","GrenadeLauncher","ShortCannon","Sniper_2","RocketLauncher","Shovel","Knife_2","Knife_1"]:
        o=bpy.data.objects.get(w)
        if o and w!=WEAPONS[variant]:
            bpy.data.objects.remove(o,do_unlink=True)
    clone_and_tint_materials(team,variant)
    path=CAT if team=="cat" else DOG
    head=extract_animal_head(path,team,hcen,hdim,arm)
    add_headset_and_goggles(head,arm,team)
    add_tail(arm,head,team)
    # Name armature and body deterministically.
    arm.name="OperatorRig"
    body=max((o for o in bpy.context.scene.objects if o.type=="MESH" and len(o.data.vertices)>2500 and o.name not in [head.name]), key=lambda x:len(x.data.vertices))
    body.name="OperatorBody"
    return arm,head

def set_idle(arm):
    idle=next((a for a in bpy.data.actions if "Idle_Shoot" in a.name),None) or next((a for a in bpy.data.actions if "|Idle_" in a.name or "|Idle" in a.name),None)
    if idle:
        if arm.animation_data is None: arm.animation_data_create()
        arm.animation_data.action=idle
        bpy.context.scene.frame_set(int(idle.frame_range[0]+2))

def make_render(team,variant,arm,out_path):
    set_idle(arm)
    # Ground
    bpy.ops.mesh.primitive_plane_add(size=16,location=(0,0,-.02))
    ground=bpy.context.object
    gm=bpy.data.materials.new("Ground"); gm.diffuse_color=(.09,.075,.06,1); gm.use_nodes=True
    bs=gm.node_tree.nodes.get("Principled BSDF"); bs.inputs["Roughness"].default_value=.84
    ground.data.materials.append(gm)
    # Camera faces the models' -Y front.
    cam_data=bpy.data.cameras.new("Camera"); cam=bpy.data.objects.new("Camera",cam_data); bpy.context.collection.objects.link(cam); bpy.context.scene.camera=cam
    target=Vector((0,0,1.08)); cam.location=Vector((3.0,-5.7,2.45))
    cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler(); cam_data.lens=58
    # Lights
    world=bpy.data.worlds.new("World"); bpy.context.scene.world=world; world.use_nodes=True
    bg=world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=((.015,.04,.08,1) if team=="cat" else (.07,.018,.012,1)); bg.inputs["Strength"].default_value=.45
    def light(loc,energy,size,color):
        d=bpy.data.lights.new("Area","AREA"); d.energy=energy; d.shape="DISK"; d.size=size; d.color=color
        o=bpy.data.objects.new("Area",d); bpy.context.collection.objects.link(o); o.location=loc; o.rotation_euler=(target-o.location).to_track_quat("-Z","Y").to_euler()
    light((-3,-4,5),900,4,(.72,.86,1.0))
    light((3,-1,3),700,3,(1.0,.47,.28))
    light((0,3,4),850,3,(1.0,.82,.62))
    sc=bpy.context.scene
    sc.render.engine="BLENDER_EEVEE"
    sc.render.resolution_x=512; sc.render.resolution_y=720; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="PNG"; sc.render.filepath=out_path
    sc.render.film_transparent=False
    sc.view_settings.look="AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(ground,do_unlink=True); bpy.data.objects.remove(cam,do_unlink=True)

def export_glb(path):
    bpy.ops.export_scene.gltf(filepath=path,export_format="GLB",export_animations=True,export_apply=True,export_lights=False,export_cameras=False)

for team in ("cat","dog"):
    for variant in range(5):
        reset()
        arm,head=prepare_soldier(team,variant)
        portrait=os.path.join(OUT,f"{team}_{variant}_portrait.png")
        make_render(team,variant,arm,portrait)
        # remove render-only lights/camera remnants if any
        for o in list(bpy.context.scene.objects):
            if o.type in {"LIGHT","CAMERA"}: bpy.data.objects.remove(o,do_unlink=True)
        set_idle(arm)
        glb=os.path.join(OUT,f"{team}_soldier_{variant}.glb")
        export_glb(glb)
        print("BUILT",glb,portrait)
