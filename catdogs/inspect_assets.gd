extends SceneTree

func _initialize():
    var paths = [
        "res://assets/character.glb",
        "res://assets/fps_props.glb",
        "res://assets/guns.glb",
        "res://assets/fpArms.glb"
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
    print(pad, n.name, " [", n.get_class(), "]", extra)
    for c in n.get_children():
        _walk(c, depth+1)
