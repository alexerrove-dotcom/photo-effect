extends SceneTree

func _initialize() -> void:
    call_deferred("_test")

func _fail(message: String) -> void:
    push_error("AURORA_V07_TEST_FAIL: " + message)
    quit(2)

func _test() -> void:
    var source := load("res://scenes/main.tscn") as PackedScene
    if source == null:
        _fail("Could not load main scene")
        return
    var game: Variant = source.instantiate()
    root.add_child(game)
    await process_frame
    await physics_frame
    var hud: Variant = game.get_node("Hud")
    var hero: Variant = game.get_node("Hero")
    var joystick: Variant = hud.joystick
    hud.show_start_menu(false)
    if not hero.movement_enabled:
        _fail("Hero never enabled after start")
        return
    var touch := InputEventScreenTouch.new()
    touch.pressed = true
    touch.index = 4
    touch.position = joystick.center + Vector2(67.0, 0.0)
    joystick._input(touch)
    if joystick.direction.length() < 0.4:
        _fail("Touch joystick failed to respond")
        return
    touch.pressed = false
    joystick._input(touch)
    var original_z: float = hero.global_position.z
    Input.action_press("move_forward", 1.0)
    for i in range(64):
        await physics_frame
    Input.action_release("move_forward")
    var delta_z: float = absf(hero.global_position.z - original_z)
    print("AURORA_V07_WALK_DISTANCE ", delta_z)
    if delta_z < 0.9:
        _fail("Character stuck and did not walk forward")
        return
    game.travel_to("winter")
    await process_frame
    var winter: Variant = game.get_node("World")
    if winter.biome != "winter" or winter.get_child_count() < 160:
        _fail("Winter level empty")
        return
    if not hud.minimap.visible:
        _fail("Winter map was not activated")
        return
    if winter.snow_texture == null:
        _fail("Snow shader texture missing")
        return
    var before: float = winter.snow_image.get_pixel(512, 512).r
    winter.stamp_snow(Vector3.ZERO)
    var after: float = winter.snow_image.get_pixel(512, 512).r
    if after < 0.4 or after <= before:
        _fail("Snow displacement texture did not record footprints")
        return
    var terrain := winter.get_node_or_null("ContinuousForestFloor") as MeshInstance3D
    if terrain == null:
        _fail("Winter terrain missing")
        return
    var shader := terrain.material_override as ShaderMaterial
    if shader == null or shader.shader == null:
        _fail("Winter terrain deformation shader missing")
        return
    print("AURORA_V07_TEST_SUCCESS: input, movement, winter scene, map, snow deformation")
    quit(0)
