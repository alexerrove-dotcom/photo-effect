extends CharacterBody3D

var game
var team := 1
var variant := 0
var hp := 100.0
var alive := true
var move_speed := 3.2
var fire_cooldown := 0.0
var decision_timer := 0.0
var roam_target := Vector3.ZERO
var head: MeshInstance3D
var body: MeshInstance3D
var gun: MeshInstance3D
var marker: Label3D

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
    capsule.height = 1.75
    shape.shape = capsule
    shape.position.y = 0.9
    add_child(shape)

    body = MeshInstance3D.new()
    var body_mesh := CapsuleMesh.new()
    body_mesh.radius = 0.43
    body_mesh.height = 1.25
    body.mesh = body_mesh
    body.position.y = 0.85
    body.material_override = game.make_mat(_body_color())
    add_child(body)

    head = MeshInstance3D.new()
    var head_mesh := SphereMesh.new()
    head_mesh.radius = 0.38
    head_mesh.height = 0.76
    head.mesh = head_mesh
    head.position = Vector3(0, 1.72, 0)
    head.material_override = game.make_mat(_fur_color())
    add_child(head)

    if team == 0:
        _add_cat_ear(Vector3(-0.23, 2.05, 0), -0.12)
        _add_cat_ear(Vector3(0.23, 2.05, 0), 0.12)
    else:
        _add_dog_ear(Vector3(-0.28, 1.96, 0), -0.18)
        _add_dog_ear(Vector3(0.28, 1.96, 0), 0.18)

    var vest := MeshInstance3D.new()
    var vest_mesh := BoxMesh.new()
    vest_mesh.size = Vector3(0.78, 0.72, 0.52)
    vest.mesh = vest_mesh
    vest.position = Vector3(0, 1.05, 0)
    vest.material_override = game.make_mat(Color("20262c") if team == 0 else Color("302421"))
    add_child(vest)

    gun = MeshInstance3D.new()
    var gun_mesh := BoxMesh.new()
    gun_mesh.size = Vector3(0.10, 0.10, 0.85)
    gun.mesh = gun_mesh
    gun.position = Vector3(0.36, 1.22, -0.52)
    gun.material_override = game.make_mat(Color("1a1d1f"), 0.65)
    add_child(gun)

    marker = Label3D.new()
    marker.text = "▼"
    marker.font_size = 40
    marker.modulate = Color("37a8ff") if team == game.player_team else Color("ff554d")
    marker.position = Vector3(0, 2.55, 0)
    marker.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    add_child(marker)

func _add_cat_ear(pos:Vector3, tilt:float) -> void:
    var ear := MeshInstance3D.new()
    var cone := CylinderMesh.new()
    cone.top_radius = 0.0
    cone.bottom_radius = 0.18
    cone.height = 0.42
    ear.mesh = cone
    ear.position = pos
    ear.rotation.z = tilt
    ear.material_override = game.make_mat(_fur_color())
    add_child(ear)

func _add_dog_ear(pos:Vector3, tilt:float) -> void:
    var ear := MeshInstance3D.new()
    var box := BoxMesh.new()
    box.size = Vector3(0.18, 0.48, 0.13)
    ear.mesh = box
    ear.position = pos
    ear.rotation.z = tilt
    ear.material_override = game.make_mat(_fur_color().darkened(0.08))
    add_child(ear)

func _fur_color() -> Color:
    var cats = [Color("d1d0ca"), Color("4f565c"), Color("f0d6ad"), Color("9199a0"), Color("c2a17d")]
    var dogs = [Color("9c6a3c"), Color("b7b4aa"), Color("704832"), Color("d8b790"), Color("4a4039")]
    return cats[variant % cats.size()] if team == 0 else dogs[variant % dogs.size()]

func _body_color() -> Color:
    var cats = [Color("195d9b"), Color("1f6eaa"), Color("254f79"), Color("2a6d8f"), Color("274a66")]
    var dogs = [Color("7b332c"), Color("8c3b31"), Color("6d2d28"), Color("99483a"), Color("5f2926")]
    return cats[variant % cats.size()] if team == 0 else dogs[variant % dogs.size()]

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
        var stop_dist := 8.5 if target != null or team != game.player_team else 2.0
        if flat.length() > stop_dist:
            velocity.x = desired.x * move_speed
            velocity.z = desired.z * move_speed
        else:
            velocity.x = move_toward(velocity.x, 0.0, 10.0 * delta)
            velocity.z = move_toward(velocity.z, 0.0, 10.0 * delta)
    else:
        velocity.x = move_toward(velocity.x, 0.0, 10.0 * delta)
        velocity.z = move_toward(velocity.z, 0.0, 10.0 * delta)

    if not is_on_floor():
        velocity.y -= 20.0 * delta
    else:
        velocity.y = 0.0
    move_and_slide()

    if target_dist < 24.0 and fire_cooldown <= 0.0:
        _shoot_target(target)

func _shoot_target(target) -> void:
    fire_cooldown = randf_range(0.35, 0.75)
    if target != null:
        var hit_chance := 0.32 + 0.10 * clampf((20.0 - global_position.distance_to(target.global_position)) / 20.0, 0.0, 1.0)
        if randf() < hit_chance:
            target.take_damage(randf_range(8.0, 17.0), self)
        game.spawn_tracer(global_position + Vector3(0, 1.35, 0), target.global_position + Vector3(0, 1.2, 0), team)
    elif team != game.player_team and game.player_alive:
        if randf() < 0.22:
            game.damage_player(randf_range(6.0, 13.0), self)
        game.spawn_tracer(global_position + Vector3(0, 1.35, 0), game.player.global_position + Vector3(0, 1.45, 0), team)

func take_damage(amount:float, attacker=null) -> void:
    if not alive:
        return
    hp -= amount
    game.spawn_hit(global_position + Vector3(0, 1.4, 0), team)
    if hp <= 0.0:
        die(attacker)

func die(attacker=null) -> void:
    if not alive:
        return
    alive = false
    collision_layer = 0
    collision_mask = 0
    if marker:
        marker.visible = false
    var tw := create_tween()
    tw.tween_property(self, "rotation:z", deg_to_rad(82.0), 0.35)
    tw.parallel().tween_property(self, "position:y", 0.16, 0.35)
    game.bot_died(self, attacker)
    await get_tree().create_timer(2.2).timeout
    visible = false

func _pick_roam_target() -> void:
    var points = [Vector3(-14,0,-14), Vector3(14,0,-14), Vector3(-14,0,14), Vector3(14,0,14), Vector3(0,0,0), Vector3(-22,0,3), Vector3(22,0,-3)]
    roam_target = points[randi() % points.size()] + Vector3(randf_range(-3,3),0,randf_range(-3,3))
