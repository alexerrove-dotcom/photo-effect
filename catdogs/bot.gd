extends CharacterBody3D

var game
var team := 1
var variant := 0
var hp := 100.0
var alive := true
var move_speed := 3.45
var fire_cooldown := 0.0
var decision_timer := 0.0
var roam_target := Vector3.ZERO
var marker: Label3D
var visual: Node3D
var anim_player: AnimationPlayer
var anim_state := ""

func setup(p_game, p_team:int, p_variant:int, pos:Vector3) -> void:
    game = p_game
    team = p_team
    variant = p_variant
    position = pos
    collision_layer = 2
    collision_mask = 1
    _build_visuals()
    _pick_roam_target()

func _build_visuals() -> void:
    var shape := CollisionShape3D.new()
    var capsule := CapsuleShape3D.new()
    capsule.radius = 0.42
    capsule.height = 1.78
    shape.shape = capsule
    shape.position.y = 0.89
    add_child(shape)

    var prefix := "cat" if team == 0 else "dog"
    var path := "res://generated/%s_soldier_%d.glb" % [prefix, variant % 5]
    if ResourceLoader.exists(path):
        var packed = load(path)
        if packed is PackedScene:
            visual = packed.instantiate()
            visual.name = "OperatorVisual"
            add_child(visual)
            _enable_shadows(visual)
            anim_player = _find_anim_player(visual)
            _play_anim("Idle_Shoot")
    if visual == null:
        _build_fallback()

    marker = Label3D.new()
    marker.text = "▼"
    marker.font_size = 38
    marker.outline_size = 8
    marker.modulate = Color("35a9ff") if team == game.player_team else Color("ff554d")
    marker.position = Vector3(0, 2.62, 0)
    marker.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    marker.no_depth_test = true
    add_child(marker)

func _enable_shadows(n:Node) -> void:
    if n is GeometryInstance3D:
        n.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
    for c in n.get_children():
        _enable_shadows(c)

func _find_anim_player(n:Node) -> AnimationPlayer:
    if n is AnimationPlayer:
        return n
    for c in n.get_children():
        var found := _find_anim_player(c)
        if found != null:
            return found
    return null

func _anim_name_contains(key:String) -> StringName:
    if anim_player == null:
        return &""
    var low := key.to_lower()
    for n in anim_player.get_animation_list():
        if low in String(n).to_lower():
            return n
    return &""

func _play_anim(key:String, force:=false) -> void:
    if anim_player == null or (not force and anim_state == key):
        return
    var n := _anim_name_contains(key)
    if n == &"":
        if key == "Run_Gun":
            n = _anim_name_contains("Run")
        elif key == "Idle_Shoot":
            n = _anim_name_contains("Idle")
    if n != &"":
        anim_player.play(n, 0.12)
        anim_state = key

func _build_fallback() -> void:
    visual = Node3D.new()
    add_child(visual)
    var body := MeshInstance3D.new()
    var body_mesh := CapsuleMesh.new()
    body_mesh.radius = 0.43
    body_mesh.height = 1.35
    body.mesh = body_mesh
    body.position.y = 0.9
    body.material_override = game.make_mat(Color("1f6296") if team == 0 else Color("7e302a"))
    visual.add_child(body)
    var head := MeshInstance3D.new()
    var hm := SphereMesh.new()
    hm.radius = 0.35
    hm.height = 0.7
    head.mesh = hm
    head.position.y = 1.72
    head.material_override = game.make_mat(Color("8c9094") if team == 0 else Color("8b5b38"))
    visual.add_child(head)

func _physics_process(delta:float) -> void:
    if not alive or game == null or not game.match_active:
        return
    fire_cooldown = maxf(0.0, fire_cooldown - delta)
    decision_timer -= delta
    if decision_timer <= 0.0:
        decision_timer = randf_range(0.35, 0.9)
        if randf() < 0.35:
            _pick_roam_target()

    var target = game.get_bot_target(self)
    var target_pos := roam_target
    var target_dist := 999.0
    if target != null:
        target_pos = target.global_position
        target_dist = global_position.distance_to(target.global_position)
    elif team != game.player_team and game.player_alive:
        target_pos = game.player.global_position
        target_dist = global_position.distance_to(game.player.global_position)

    var flat := target_pos - global_position
    flat.y = 0.0
    if flat.length() > 0.2:
        look_at(global_position + flat, Vector3.UP)
        var desired := flat.normalized()
        var stop_dist := 8.0 if target != null or team != game.player_team else 2.0
        if flat.length() > stop_dist:
            velocity.x = desired.x * move_speed
            velocity.z = desired.z * move_speed
        else:
            velocity.x = move_toward(velocity.x, 0.0, 11.0 * delta)
            velocity.z = move_toward(velocity.z, 0.0, 11.0 * delta)
    else:
        velocity.x = move_toward(velocity.x, 0.0, 11.0 * delta)
        velocity.z = move_toward(velocity.z, 0.0, 11.0 * delta)

    if not is_on_floor():
        velocity.y -= 20.0 * delta
    else:
        velocity.y = 0.0
    move_and_slide()

    if Vector2(velocity.x, velocity.z).length() > 0.45:
        _play_anim("Run_Gun")
    else:
        _play_anim("Idle_Shoot")

    if target_dist < 25.0 and fire_cooldown <= 0.0:
        _shoot_target(target)

func _shoot_target(target) -> void:
    fire_cooldown = randf_range(0.32, 0.72)
    _play_anim("Idle_Shoot", true)
    if target != null:
        var hit_chance := 0.34 + 0.12 * clampf((20.0 - global_position.distance_to(target.global_position)) / 20.0, 0.0, 1.0)
        if randf() < hit_chance:
            target.take_damage(randf_range(8.0, 17.0), self)
        game.spawn_tracer(global_position + Vector3(0, 1.35, 0), target.global_position + Vector3(0, 1.2, 0), team)
    elif team != game.player_team and game.player_alive:
        if randf() < 0.23:
            game.damage_player(randf_range(6.0, 13.0), self)
        game.spawn_tracer(global_position + Vector3(0, 1.35, 0), game.player.global_position + Vector3(0, 1.45, 0), team)

func take_damage(amount:float, attacker=null) -> void:
    if not alive:
        return
    hp -= amount
    game.spawn_hit(global_position + Vector3(0, 1.35, 0), team)
    if hp <= 0.0:
        die(attacker)
    else:
        _play_anim("HitReact", true)

func die(attacker=null) -> void:
    if not alive:
        return
    alive = false
    collision_layer = 0
    collision_mask = 0
    if marker:
        marker.visible = false
    var death := _anim_name_contains("Death")
    if anim_player != null and death != &"":
        anim_player.play(death, 0.08)
    else:
        var tw := create_tween()
        tw.tween_property(self, "rotation:z", deg_to_rad(82.0), 0.35)
    game.bot_died(self, attacker)
    await get_tree().create_timer(2.3).timeout
    visible = false

func _pick_roam_target() -> void:
    var points = [Vector3(-14,0,-14), Vector3(14,0,-14), Vector3(-14,0,14), Vector3(14,0,14), Vector3(0,0,0), Vector3(-22,0,3), Vector3(22,0,-3)]
    roam_target = points[randi() % points.size()] + Vector3(randf_range(-3,3),0,randf_range(-3,3))
