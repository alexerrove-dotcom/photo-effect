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

def tint_head_materials(head,team,variant):
    cat_fur=[(.45,.47,.50,1),(.78,.30,.08,1),(.82,.82,.80,1),(.36,.24,.16,1),(.055,.06,.065,1)]
    dog_fur=[(.42,.23,.11,1),(.42,.46,.50,1),(.68,.48,.30,1),(.12,.09,.075,1),(.055,.055,.05,1)]
    fur=cat_fur[variant] if team=="cat" else dog_fur[variant]
    for slot in head.material_slots:
        m=slot.material
        if not m: continue
        nm=m.copy(); slot.material=nm
        n=(m.name or "").lower()
        if "eye" in n:
            continue
        if "ear" in n:
            col=(max(.06,fur[0]*.65), max(.045,fur[1]*.55), max(.05,fur[2]*.55),1)
        else:
            col=fur
        nm.diffuse_color=col
        if nm.use_nodes and nm.node_tree:
            bs=nm.node_tree.nodes.get("Principled BSDF")
            if bs:
                bs.inputs["Base Color"].default_value=col
                bs.inputs["Roughness"].default_value=.78

def join_into_head(head, objects):
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    for o in objects:
        if o and o.name in bpy.data.objects:
            o.select_set(True)
    bpy.context.view_layer.objects.active=head
    bpy.ops.object.join()

def extract_animal_head(path, team, variant, target_center, target_dims, human_head):
    # Keep the original human Head object itself because the source GLB already parents it
    # correctly to the animated Head bone. Replace only its mesh contents.
    human_head.data=bpy.data.meshes.new(("CatHeadMesh" if team=="cat" else "DogHeadMesh"))
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new=[o for o in bpy.context.scene.objects if o not in before]
    animal_mesh=max((o for o in new if o.type=="MESH" and o.name!="Icosphere"),key=lambda o:len(o.data.vertices))

    # Bake the source animal's current armature deformation, then detach it as clean geometry.
    bpy.ops.object.select_all(action="DESELECT")
    animal_mesh.select_set(True); bpy.context.view_layer.objects.active=animal_mesh
    for mod in list(animal_mesh.modifiers):
        if mod.type=="ARMATURE":
            try: bpy.ops.object.modifier_apply(modifier=mod.name)
            except: pass

    # Spatially keep only the animal's head. Both source animals are Z-up after glTF import.
    cutoff=.54 if team=="cat" else .90
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for v in animal_mesh.data.vertices:
        v.select=(animal_mesh.matrix_world@v.co).z >= cutoff
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="INVERT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")

    mw=animal_mesh.matrix_world.copy()
    animal_mesh.parent=None
    animal_mesh.matrix_world=mw

    # Animal source meshes face the opposite Y direction from the soldier rig.
    # Turn them around the Blender Z-up axis so eyes/muzzle face the weapon/camera side.
    animal_mesh.rotation_euler.z += math.pi
    bpy.context.view_layer.update()
    for o in list(new):
        if o is animal_mesh: continue
        bpy.data.objects.remove(o,do_unlink=True)

    # Fit the real animal head into the original animated human head's world-space envelope.
    mn,mx,dim,cen=mesh_bounds(animal_mesh)
    desired=Vector((target_dims.x*1.00,target_dims.y*(1.12 if team=="dog" else 1.03),target_dims.z*1.02))
    animal_mesh.scale.x*=desired.x/max(dim.x,.001)
    animal_mesh.scale.y*=desired.y/max(dim.y,.001)
    animal_mesh.scale.z*=desired.z/max(dim.z,.001)
    bpy.context.view_layer.update()
    _,_,_,cen2=mesh_bounds(animal_mesh)
    animal_mesh.location += target_center-cen2
    animal_mesh.location.y += (-.045 if team=="dog" else -.01)
    bpy.context.view_layer.update()
    tint_head_materials(animal_mesh,team,variant)

    # Joining into the *original Head object* preserves its proven bone-parent relationship.
    join_into_head(human_head,[animal_mesh])
    human_head.name=("CatHead" if team=="cat" else "DogHead")
    return human_head

def add_uv(name,loc,scale,color):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    m=bpy.data.materials.new(name+"Mat"); m.diffuse_color=color; m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    if bs:
        bs.inputs["Base Color"].default_value=color
        bs.inputs["Roughness"].default_value=.34
        bs.inputs["Metallic"].default_value=.26 if color[0]<.2 else .0
    o.data.materials.append(m)
    return o

def parent_parts_to_head(head,parts):
    for o in parts:
        if not o or o.name not in bpy.data.objects:
            continue
        world=o.matrix_world.copy()
        o.parent=head
        o.matrix_parent_inverse=head.matrix_world.inverted()
        o.matrix_world=world

def add_animal_face_details(head,team,variant):
    mn,mx,d,c=mesh_bounds(head)
    parts=[]
    # Front of the operator faces -Y in the soldier rig/render.
    eye_z=c.z+d.z*.105
    eye_y=mn.y-d.y*.045
    eye_dx=d.x*.185
    iris_cols=[(.15,.70,.95,1),(.42,.82,.34,1),(.96,.68,.18,1),(.42,.65,.92,1),(.72,.82,.92,1)]
    iris=iris_cols[variant % len(iris_cols)]
    for sx in (-1,1):
        parts.append(add_uv("EyeWhite",Vector((c.x+sx*eye_dx,eye_y,eye_z)),
                   Vector((d.x*.105,d.y*.055,d.z*.105)),(.92,.94,.90,1)))
        parts.append(add_uv("Iris",Vector((c.x+sx*eye_dx,eye_y-d.y*.050,eye_z)),
                   Vector((d.x*.055,d.y*.028,d.z*.060)),iris))
        parts.append(add_uv("Pupil",Vector((c.x+sx*eye_dx,eye_y-d.y*.078,eye_z)),
                   Vector((d.x*.024,d.y*.016,d.z*.050)),(.012,.014,.012,1)))
    if team=="cat":
        cheek=(.70,.68,.62,1) if variant!=4 else (.20,.21,.22,1)
        for sx in (-1,1):
            parts.append(add_uv("CatMuzzle",Vector((c.x+sx*d.x*.105,mn.y-d.y*.035,c.z-d.z*.115)),
                       Vector((d.x*.15,d.y*.095,d.z*.115)),cheek))
        parts.append(add_uv("CatNose",Vector((c.x,mn.y-d.y*.145,c.z-d.z*.055)),
                   Vector((d.x*.070,d.y*.050,d.z*.055)),(.055,.035,.035,1)))
    else:
        # A pronounced dog snout makes the silhouette clearly canine from FPS distance.
        muzzle=(.42,.31,.22,1) if variant in (0,2,3) else (.58,.58,.55,1)
        parts.append(add_uv("DogMuzzle",Vector((c.x,mn.y-d.y*.105,c.z-d.z*.105)),
                   Vector((d.x*.235,d.y*.180,d.z*.155)),muzzle))
        parts.append(add_uv("DogNose",Vector((c.x,mn.y-d.y*.285,c.z-d.z*.060)),
                   Vector((d.x*.135,d.y*.065,d.z*.085)),(.025,.025,.022,1)))
    parent_parts_to_head(head,parts)

def add_headset_and_goggles(head,team):
    mn,mx,d,c=mesh_bounds(head)
    glass=(.015,.065,.09,1)
    pieces=[]
    for sx in (-1,1):
        pieces.append(add_uv("Goggle",Vector((c.x+sx*d.x*.20,mn.y-.025,c.z+d.z*.05)),
               Vector((d.x*.145,d.y*.045,d.z*.10)),glass))
    for sx in (-1,1):
        pieces.append(add_uv("Headset",Vector((c.x+sx*d.x*.50,c.y+d.y*.04,c.z+d.z*.05)),
               Vector((d.x*.085,d.y*.12,d.z*.155)),(.022,.028,.032,1)))
    # Helmet sits only over the upper skull; it deliberately does not cover the muzzle/eyes.
    pieces.append(add_uv("Helmet",Vector((c.x,c.y+d.y*.16,c.z+d.z*.38)),
           Vector((d.x*.50,d.y*.39,d.z*.25)),(.028,.038,.043,1)))
    parent_parts_to_head(head,pieces)

def prepare_soldier(team,variant):
    bpy.ops.import_scene.gltf(filepath=SOLDIER)
    arm=next(o for o in bpy.context.scene.objects if o.type=="ARMATURE")
    for o in list(bpy.context.scene.objects):
        if o.name.startswith("Icosphere"): bpy.data.objects.remove(o,do_unlink=True)

    human_head=next(o for o in bpy.context.scene.objects if o.type=="MESH" and o.name=="Head")
    hmn,hmx,hdim,hcen=mesh_bounds(human_head)

    # Keep one genuine weapon mesh per operator.
    for w in ["AK","SMG","Shotgun","Sniper","Pistol","Revolver","Revolver_Small","GrenadeLauncher","ShortCannon","Sniper_2","RocketLauncher","Shovel","Knife_2","Knife_1"]:
        o=bpy.data.objects.get(w)
        if o and w!=WEAPONS[variant]:
            bpy.data.objects.remove(o,do_unlink=True)

    clone_and_tint_materials(team,variant)
    head=extract_animal_head(CAT if team=="cat" else DOG,team,variant,hcen,hdim,human_head)
    add_animal_face_details(head,team,variant)
    add_headset_and_goggles(head,team)

    arm.name="OperatorRig"
    body=max((o for o in bpy.context.scene.objects if o.type=="MESH" and len(o.data.vertices)>2500 and o is not head), key=lambda x:len(x.data.vertices))
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
