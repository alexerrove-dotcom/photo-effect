extends SceneTree

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    printerr("RIG TEST FAILED: " + message)
    quit(1)

func _run() -> void:
    var packed: PackedScene = load("res://scenes/main.tscn")
    if packed == null:
        _fail("Scene not loadable")
        return
    var editor = packed.instantiate()
    root.add_child(editor)
    await process_frame
    if editor.original_meshes.is_empty():
        _fail("Demo has no meshes")
        return
    editor._generate_humanoid_rig()
    if editor.skeleton == null or editor.skeleton.get_bone_count() < 10:
        _fail("Rig did not generate")
        return
    var bone: int = editor.skeleton.find_bone("LowerLeg.L")
    if bone < 0:
        _fail("Knee bone missing")
        return
    editor.selected_bone = bone
    var original: Vector3 = editor.skeleton.get_bone_global_rest(bone).origin
    editor._move_bone_to_world(editor.skeleton.to_global(original + Vector3(0.08, 0, 0)))
    if absf(editor.skeleton.get_bone_global_rest(bone).origin.x - original.x - 0.08) > 0.01:
        _fail("Rest pose joint drag failed")
        return
    await editor._apply_skinning()
    await process_frame
    if editor.generated_meshes.is_empty():
        _fail("Skinning yielded zero meshes")
        return
    var skinned: MeshInstance3D = editor.generated_meshes[0]
    if skinned.skin == null or skinned.skin.get_bind_count() != editor.skeleton.get_bone_count():
        _fail("Skin binds are missing")
        return
    var arrays: Array = skinned.mesh.surface_get_arrays(0)
    var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
    var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
    if weights.size() != verts.size() * 4:
        _fail("Skin weight arrays mismatch")
        return
    var old_pose: Vector3 = editor.skeleton.get_bone_global_pose(bone).origin
    editor._move_bone_to_world(editor.skeleton.to_global(old_pose + Vector3(0.21, 0, 0)))
    await process_frame
    var new_pose: Vector3 = editor.skeleton.get_bone_global_pose(bone).origin
    if absf(new_pose.x - old_pose.x - 0.21) > 0.01:
        _fail("Pose bone did not follow")
        return
    editor._toggle_animation("walk")
    for i in 8:
        await process_frame
    var thigh_idx: int = editor.skeleton.find_bone("UpperLeg.L")
    var quat: Quaternion = editor.skeleton.get_bone_pose_rotation(thigh_idx)
    if quat.angle() < 0.001:
        _fail("Walk animation does not change pose")
        return
    print("RIG TEST PASS: generated bones, rest-position, skin binds, vertex weights, pose movement and walk animation")
    quit(0)
