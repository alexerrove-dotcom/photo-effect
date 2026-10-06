extends SceneTree

func _initialize():
    var paths = [
        "res://assets/character.glb",
        "res://assets/buildings.glb",
        "res://assets/props.glb",
        "res://assets/vehicles.glb"
    ]
    for p in paths:
        print("=== ASSET ", p, " ===")
        var r = load(p)
        if r == null:
            print("LOAD_FAILED")
            continue
        var n = r.instantiate()
        _walk(n, 0)
        n.queue_free()
    quit()

func _walk(n:Node, depth:int):
    var pad = "  ".repeat(depth)
    var extra = ""
    if n is MeshInstance3D and n.mesh != null:
        var a = n.mesh.get_aabb()
        extra = " AABB=" + str(a)
    if n is Skeleton3D:
        extra += " BONES=" + str(n.get_bone_count())
        if n.get_bone_count() > 0:
            var names=[]
            for i in range(min(n.get_bone_count(), 20)):
                names.append(n.get_bone_name(i))
            extra += " " + str(names)
    print(pad, n.name, " [", n.get_class(), "]", extra)
    for c in n.get_children():
        _walk(c, depth+1)
