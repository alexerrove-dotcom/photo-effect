extends Node3D

const BOT_SCRIPT = preload("res://bot.gd")
const MINIMAP_SCRIPT = preload("res://minimap.gd")

var player_team := 0
var player_variant := 0
var player: CharacterBody3D
var camera: Camera3D
var weapon_root: Node3D
var muzzle_light: OmniLight3D
var bots: Array = []
var match_active := false
var player_alive := true
var player_hp := 100.0
var armor := 100.0
var ammo := 30
var reserve := 90
var mag_size := 30
var fire_delay := 0.105
var fire_cd := 0.0
var reloading := false
var firing := false
var aiming := false
var crouched := false
var yaw := 0.0
var pitch := 0.0
var left_touch := -1
var look_touch := -1
var joy_origin := Vector2.ZERO
var joy_pos := Vector2.ZERO
var joy_vec := Vector2.ZERO
var joy_radius := 92.0
var round_time := 100.0
var score_cats := 0
var score_dogs := 0
var round_number := 1
var c4_planted := false
var bomb_time := 35.0
var planted_site := Vector3.ZERO
var money := 4750
var round_ending := false
var hud: CanvasLayer
var menu: CanvasLayer
var status_label: Label
var ammo_label: Label
var hp_label: Label
var armor_label: Label
var money_label: Label
var timer_label: Label
var score_label: Label
var banner_label: Label
var plant_button: Button
var grenade_button: Button
var reload_button: Button
var shoot_button: Button
var aim_button: Button
var crouch_button: Button
var minimap
var joy_base: Control
var joy_knob: Control
var rng := RandomNumberGenerator.new()

func _ready() -> void:
    rng.randomize()
    _build_environment()
    _build_map()
    _build_player()
    _build_hud()
    _build_menu()
    _set_match_ui(false)

func make_mat(color:Color, metallic:float=0.0, roughness:float=0.78, alpha:float=1.0) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = Color(color.r, color.g, color.b, alpha)
    m.metallic = metallic
    m.roughness = roughness
    if alpha < 0.999:
        m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
        m.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
    return m

func _build_environment() -> void:
    var env := WorldEnvironment.new()
    var e := Environment.new()
    e.background_mode = Environment.BG_SKY
    var sky := Sky.new()
    var sm := ProceduralSkyMaterial.new()
    sm.sky_top_color = Color("3f91d1")
    sm.sky_horizon_color = Color("cfe7ef")
    sm.ground_bottom_color = Color("8b7158")
    sm.ground_horizon_color = Color("d8c7a6")
    sm.sun_angle_max = 28.0
    sky.sky_material = sm
    e.sky = sky
    e.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
    e.ambient_light_energy = 0.65
    e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    e.glow_enabled = true
    e.glow_intensity = 0.8
    e.fog_enabled = true
    e.fog_light_color = Color("d7cdbd")
    e.fog_density = 0.004
    env.environment = e
    add_child(env)

    var sun := DirectionalLight3D.new()
    sun.light_color = Color("fff3d0")
    sun.light_energy = 1.55
    sun.shadow_enabled = true
    sun.rotation_degrees = Vector3(-48,-34,0)
    add_child(sun)

func _build_map() -> void:
    _add_static_box(Vector3(64,0.35,64), Vector3(0,-0.18,0), Color("b7a27f"))
    var lane := Color("8f8069")
    _add_static_box(Vector3(8,0.08,58), Vector3(0,0.02,0), lane)
    _add_static_box(Vector3(56,0.08,8), Vector3(0,0.02,0), lane)

    var stone = [Color("c9b58f"), Color("bca67f"), Color("d1bf9a"), Color("a98f6c")]
    var blocks = [
        [Vector3(8,7,14),Vector3(-22,3.5,-17)], [Vector3(9,9,12),Vector3(-21,4.5,17)],
        [Vector3(11,8,9),Vector3(21,4,-20)], [Vector3(10,6,15),Vector3(22,3,17)],
        [Vector3(8,5,8),Vector3(-11,2.5,20)], [Vector3(8,6,8),Vector3(12,3,-19)]
    ]
    for i in range(blocks.size()):
        _add_static_box(blocks[i][0], blocks[i][1], stone[i % stone.size()])
        _add_rooftop_details(blocks[i][1], blocks[i][0])

    for z in [-22.0,-10.0,4.0,18.0]:
        _add_wall_segment(Vector3(-8,1.8,z), Vector3(0.6,3.6,7.0))
        _add_wall_segment(Vector3(8,1.8,z+3.0), Vector3(0.6,3.6,6.0))
    for x in [-18.0,-5.0,9.0,20.0]:
        _add_wall_segment(Vector3(x,1.8,-7), Vector3(6.0,3.6,0.6))
        _add_wall_segment(Vector3(x+2.0,1.8,9), Vector3(5.0,3.6,0.6))

    for p in [Vector3(-4,0.7,-5),Vector3(4,0.7,-3),Vector3(-2,0.7,11),Vector3(11,0.7,5),Vector3(-15,0.7,2),Vector3(17,0.7,-5)]:
        _add_crate(p)
    for p in [Vector3(-15,0.55,-10), Vector3(14,0.55,10), Vector3(-8,0.55,16), Vector3(7,0.55,-16)]:
        _add_barrel(p)

    _add_site(Vector3(-14,0.05,-14), "A")
    _add_site(Vector3(14,0.05,14), "B")

    for x in [-26.0,-18.0,18.0,26.0]:
        _add_palm(Vector3(x,0,-4 if x < 0 else 4))

func _add_static_box(size:Vector3, pos:Vector3, color:Color, metallic:float=0.0) -> StaticBody3D:
    var body := StaticBody3D.new()
    body.position = pos
    body.collision_layer = 1
    var mesh := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = size
    mesh.mesh = bm
    mesh.material_override = make_mat(color, metallic)
    body.add_child(mesh)
    var cs := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = size
    cs.shape = shape
    body.add_child(cs)
    add_child(body)
    return body

func _add_wall_segment(pos:Vector3, size:Vector3) -> void:
    var wall := _add_static_box(size, pos, Color("b8a07c"))
    var cap := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = Vector3(size.x+0.08,0.12,size.z+0.08)
    cap.mesh = bm
    cap.position.y = size.y*0.5 + 0.06
    cap.material_override = make_mat(Color("76624c"))
    wall.add_child(cap)

func _add_rooftop_details(center:Vector3, size:Vector3) -> void:
    var antenna := MeshInstance3D.new()
    var cm := CylinderMesh.new()
    cm.top_radius = 0.05
    cm.bottom_radius = 0.07
    cm.height = 2.0
    antenna.mesh = cm
    antenna.position = center + Vector3(size.x*0.25,size.y*0.5+1.0,size.z*0.2)
    antenna.material_override = make_mat(Color("4e5357"),0.75,0.35)
    add_child(antenna)

func _add_crate(pos:Vector3) -> void:
    var c := _add_static_box(Vector3(1.7,1.4,1.7), pos, Color("815c35"))
    for yy in [-0.45,0.45]:
        var band := MeshInstance3D.new()
        var bm := BoxMesh.new()
        bm.size = Vector3(1.78,0.08,1.78)
        band.mesh = bm
        band.position.y = yy
        band.material_override = make_mat(Color("34291f"),0.3,0.5)
        c.add_child(band)

func _add_barrel(pos:Vector3) -> void:
    var body := StaticBody3D.new()
    body.position = pos
    body.collision_layer = 1
    var mesh := MeshInstance3D.new()
    var cm := CylinderMesh.new()
    cm.top_radius = 0.45
    cm.bottom_radius = 0.45
    cm.height = 1.1
    mesh.mesh = cm
    mesh.material_override = make_mat(Color("294e54"),0.55,0.42)
    body.add_child(mesh)
    var cs := CollisionShape3D.new()
    var sh := CylinderShape3D.new()
    sh.radius = 0.45
    sh.height = 1.1
    cs.shape = sh
    body.add_child(cs)
    add_child(body)

func _add_site(pos:Vector3, letter:String) -> void:
    var disc := MeshInstance3D.new()
    var cm := CylinderMesh.new()
    cm.top_radius = 2.5
    cm.bottom_radius = 2.5
    cm.height = 0.04
    disc.mesh = cm
    disc.position = pos
    disc.material_override = make_mat(Color("9b302b"),0.0,0.9,0.72)
    add_child(disc)
    var l := Label3D.new()
    l.text = letter
    l.font_size = 180
    l.outline_size = 16
    l.modulate = Color("f4e4cf")
    l.position = pos + Vector3(0,0.06,0)
    l.rotation_degrees.x = -90
    add_child(l)

func _add_palm(pos:Vector3) -> void:
    var trunk := MeshInstance3D.new()
    var cm := CylinderMesh.new()
    cm.top_radius = 0.16
    cm.bottom_radius = 0.28
    cm.height = 5.8
    trunk.mesh = cm
    trunk.position = pos + Vector3(0,2.9,0)
    trunk.material_override = make_mat(Color("8a5a34"))
    add_child(trunk)
    for i in range(7):
        var leaf := MeshInstance3D.new()
        var bm := BoxMesh.new()
        bm.size = Vector3(0.22,0.06,3.1)
        leaf.mesh = bm
        leaf.position = pos + Vector3(0,5.75,0)
        leaf.rotation.y = i * TAU / 7.0
        leaf.rotation.x = deg_to_rad(-18)
        leaf.translate_object_local(Vector3(0,0,-1.25))
        leaf.material_override = make_mat(Color("386b45"))
        add_child(leaf)

func _build_player() -> void:
    player = CharacterBody3D.new()
    player.collision_layer = 0
    player.collision_mask = 1
    var cs := CollisionShape3D.new()
    var cap := CapsuleShape3D.new()
    cap.radius = 0.42
    cap.height = 1.75
    cs.shape = cap
    cs.position.y = 0.9
    player.add_child(cs)
    camera = Camera3D.new()
    camera.position = Vector3(0,1.62,0)
    camera.fov = 78.0
    player.add_child(camera)
    add_child(player)
    _build_weapon()

func _build_weapon() -> void:
    weapon_root = Node3D.new()
    weapon_root.position = Vector3(0.42,-0.42,-0.92)
    camera.add_child(weapon_root)
    var receiver := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = Vector3(0.20,0.19,0.76)
    receiver.mesh = bm
    receiver.material_override = make_mat(Color("15191c"),0.76,0.28)
    weapon_root.add_child(receiver)
    var stock := MeshInstance3D.new()
    var sm := BoxMesh.new()
    sm.size = Vector3(0.19,0.22,0.42)
    stock.mesh = sm
    stock.position = Vector3(0.0,-0.02,0.48)
    stock.material_override = make_mat(Color("292c2e"),0.55,0.38)
    weapon_root.add_child(stock)
    var barrel := MeshInstance3D.new()
    var cm := CylinderMesh.new()
    cm.top_radius = 0.045
    cm.bottom_radius = 0.055
    cm.height = 0.85
    barrel.mesh = cm
    barrel.rotation_degrees.x = 90
    barrel.position = Vector3(0.0,0.02,-0.74)
    barrel.material_override = make_mat(Color("101316"),0.82,0.2)
    weapon_root.add_child(barrel)
    var sight := MeshInstance3D.new()
    var sight_mesh := BoxMesh.new()
    sight_mesh.size = Vector3(0.12,0.16,0.21)
    sight.mesh = sight_mesh
    sight.position = Vector3(0,0.17,-0.12)
    sight.material_override = make_mat(Color("202529"),0.7,0.24)
    weapon_root.add_child(sight)
    muzzle_light = OmniLight3D.new()
    muzzle_light.light_color = Color("ffb34a")
    muzzle_light.light_energy = 0.0
    muzzle_light.omni_range = 4.0
    muzzle_light.position = Vector3(0,0,-1.18)
    weapon_root.add_child(muzzle_light)

func _build_hud() -> void:
    hud = CanvasLayer.new()
    hud.layer = 5
    add_child(hud)

    minimap = MINIMAP_SCRIPT.new()
    minimap.game = self
    minimap.position = Vector2(26,22)
    minimap.size = Vector2(190,190)
    hud.add_child(minimap)
    _hud_label("A", Vector2(65,38), 34, Color("ffbd38"))
    _hud_label("B", Vector2(162,156), 34, Color("ff5a52"))

    var top := _panel(Vector2(720,16), Vector2(480,92), Color(0.02,0.05,0.08,0.88), hud)
    score_label = _label(top,"0     0",Vector2(22,7),Vector2(436,40),31,Color.WHITE,HORIZONTAL_ALIGNMENT_CENTER)
    timer_label = _label(top,"01:40",Vector2(22,46),Vector2(436,35),25,Color("dcecf2"),HORIZONTAL_ALIGNMENT_CENTER)

    money_label = _hud_label("$ 4750", Vector2(28,238), 36, Color("ffc04c"))
    hp_label = _hud_label("✚ 100", Vector2(42,990), 34, Color.WHITE)
    armor_label = _hud_label("◆ 100", Vector2(230,990), 34, Color("8cd9ff"))
    ammo_label = _hud_label("30 / 90", Vector2(1510,24), 40, Color.WHITE)
    status_label = _hud_label("M4A1", Vector2(1510,75), 24, Color("d7e3e8"))

    banner_label = _hud_label("ОПЕРАЦИЯ НАЧАЛАСЬ", Vector2(680,130), 34, Color("76e1ea"))
    banner_label.size = Vector2(560,62)
    banner_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    banner_label.add_theme_stylebox_override("normal", _style(Color(0.02,0.06,0.08,0.90), Color(0.1,0.18,0.22,1), 2, 12))

    _make_crosshair()
    _make_joystick()

    shoot_button = _action_button("●", Vector2(1670,620), Vector2(170,170), 52)
    shoot_button.button_down.connect(func(): firing = true)
    shoot_button.button_up.connect(func(): firing = false)
    aim_button = _action_button("◎", Vector2(1690,420), Vector2(135,135), 48)
    aim_button.pressed.connect(_toggle_aim)
    grenade_button = _action_button("G", Vector2(1518,548), Vector2(120,120), 38)
    grenade_button.pressed.connect(_throw_grenade)
    reload_button = _action_button("↻", Vector2(1510,710), Vector2(115,115), 48)
    reload_button.pressed.connect(_reload)
    crouch_button = _action_button("C", Vector2(1660,820), Vector2(115,115), 38)
    crouch_button.pressed.connect(_toggle_crouch)
    plant_button = _action_button("C4", Vector2(1430,870), Vector2(150,92), 30)
    plant_button.pressed.connect(_plant_or_defuse)

func _build_menu() -> void:
    menu = CanvasLayer.new()
    menu.layer = 20
    add_child(menu)
    var bg := ColorRect.new()
    bg.color = Color("07111d")
    bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    menu.add_child(bg)

    var split := ColorRect.new()
    split.color = Color(0.16,0.02,0.02,0.46)
    split.position = Vector2(960,0)
    split.size = Vector2(960,1080)
    bg.add_child(split)
    var blue := ColorRect.new()
    blue.color = Color(0.01,0.15,0.29,0.48)
    blue.position = Vector2(0,0)
    blue.size = Vector2(960,1080)
    bg.add_child(blue)

    var title := _label(bg,"CAT vs DOGS",Vector2(390,82),Vector2(1140,120),78,Color.WHITE,HORIZONTAL_ALIGNMENT_CENTER)
    title.add_theme_color_override("font_shadow_color", Color(0,0,0,0.8))
    title.add_theme_constant_override("shadow_offset_x", 4)
    title.add_theme_constant_override("shadow_offset_y", 4)
    _label(bg,"WAR ZONE",Vector2(650,190),Vector2(620,56),34,Color("ffc34e"),HORIZONTAL_ALIGNMENT_CENTER)
    _label(bg,"КОТЫ",Vector2(90,310),Vector2(740,70),44,Color("53b9ff"),HORIZONTAL_ALIGNMENT_CENTER)
    _label(bg,"СОБАКИ",Vector2(1090,310),Vector2(740,70),44,Color("ff6960"),HORIZONTAL_ALIGNMENT_CENTER)

    for i in range(5):
        var cb := _menu_card(bg, Vector2(80+i*155,420), Vector2(138,230), "КОТ %d" % (i+1), Color("2385d5"), i, 0)
        var db := _menu_card(bg, Vector2(1080+i*155,420), Vector2(138,230), "ПЁС %d" % (i+1), Color("c7443d"), i, 1)
        cb.tooltip_text = "Штурм / разведка / поддержка"
        db.tooltip_text = "Штурм / защита / контроль"

    var start := Button.new()
    start.text = "ИГРАТЬ"
    start.position = Vector2(710,760)
    start.size = Vector2(500,100)
    start.add_theme_font_size_override("font_size",40)
    start.add_theme_stylebox_override("normal", _style(Color("e99e25"), Color("ffd36d"), 3, 16))
    start.add_theme_stylebox_override("hover", _style(Color("ffb33b"), Color.WHITE, 3, 16))
    start.add_theme_color_override("font_color",Color("101317"))
    start.pressed.connect(start_match)
    bg.add_child(start)
    _label(bg,"5 × 5 • C4 • БОТЫ • ГРАНАТЫ • МОБИЛЬНОЕ УПРАВЛЕНИЕ",Vector2(490,900),Vector2(940,55),24,Color("b9d1df"),HORIZONTAL_ALIGNMENT_CENTER)
    _label(bg,"Облачная Android-сборка • собственная карта и персонажи",Vector2(540,958),Vector2(840,45),20,Color("6d899b"),HORIZONTAL_ALIGNMENT_CENTER)

func _menu_card(parent:Control, pos:Vector2, sz:Vector2, text:String, color:Color, variant:int, team:int) -> Button:
    var b := Button.new()
    b.text = text + "\n\n" + ("▲  ◉  ▲" if team == 0 else "◆  ◉  ◆")
    b.position = pos
    b.size = sz
    b.add_theme_font_size_override("font_size",20)
    b.add_theme_stylebox_override("normal", _style(color.darkened(0.62), color, 3, 10))
    b.add_theme_stylebox_override("hover", _style(color.darkened(0.40), color.lightened(0.2), 4, 10))
    b.add_theme_stylebox_override("pressed", _style(color.darkened(0.25), Color.WHITE, 4, 10))
    b.pressed.connect(func(): _choose_character(team,variant))
    parent.add_child(b)
    return b

func _choose_character(team:int, variant:int) -> void:
    player_team = team
    player_variant = variant
    _flash_menu_choice(team,variant)

func _flash_menu_choice(team:int, variant:int) -> void:
    var who := "КОТЫ" if team == 0 else "СОБАКИ"
    var note := Label.new()
    note.text = "ВЫБРАНО: %s • БОЕЦ %d" % [who,variant+1]
    note.position = Vector2(735,690)
    note.size = Vector2(450,50)
    note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    note.add_theme_font_size_override("font_size",22)
    note.add_theme_color_override("font_color",Color("7fe8ff") if team == 0 else Color("ff8b83"))
    menu.add_child(note)
    var tw := create_tween()
    tw.tween_interval(0.8)
    tw.tween_property(note,"modulate:a",0.0,0.4)
    tw.tween_callback(note.queue_free)

func _panel(pos:Vector2, sz:Vector2, color:Color, parent:Node) -> Panel:
    var p := Panel.new()
    p.position = pos
    p.size = sz
    p.add_theme_stylebox_override("panel", _style(color, Color(0.15,0.25,0.30,0.85), 2, 12))
    parent.add_child(p)
    return p

func _style(bg:Color, border:Color, width:int=2, radius:int=8) -> StyleBoxFlat:
    var s := StyleBoxFlat.new()
    s.bg_color = bg
    s.border_color = border
    s.set_border_width_all(width)
    s.set_corner_radius_all(radius)
    return s

func _label(parent:Node, text:String, pos:Vector2, sz:Vector2, fs:int, color:Color, align:int=HORIZONTAL_ALIGNMENT_LEFT) -> Label:
    var l := Label.new()
    l.text = text
    l.position = pos
    l.size = sz
    l.add_theme_font_size_override("font_size",fs)
    l.add_theme_color_override("font_color",color)
    l.horizontal_alignment = align
    l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
    parent.add_child(l)
    return l

func _hud_label(text:String, pos:Vector2, fs:int, color:Color) -> Label:
    return _label(hud,text,pos,Vector2(340,58),fs,color)

func _action_button(text:String, pos:Vector2, sz:Vector2, fs:int) -> Button:
    var b := Button.new()
    b.text = text
    b.position = pos
    b.size = sz
    b.add_theme_font_size_override("font_size",fs)
    b.add_theme_color_override("font_color",Color.WHITE)
    b.add_theme_stylebox_override("normal", _style(Color(0.04,0.06,0.07,0.48),Color(0.86,0.91,0.92,0.8),2,int(sz.x*0.5)))
    b.add_theme_stylebox_override("pressed", _style(Color(0.18,0.33,0.38,0.72),Color.WHITE,3,int(sz.x*0.5)))
    hud.add_child(b)
    return b

func _make_crosshair() -> void:
    var c := Control.new()
    c.position = Vector2(960,540)
    c.mouse_filter = Control.MOUSE_FILTER_IGNORE
    hud.add_child(c)
    for r in [Rect2(-22,-1,14,2),Rect2(8,-1,14,2),Rect2(-1,-22,2,14),Rect2(-1,8,2,14)]:
        var q := ColorRect.new()
        q.color = Color(1,1,1,0.9)
        q.position = r.position
        q.size = r.size
        c.add_child(q)

func _make_joystick() -> void:
    joy_base = Control.new()
    joy_base.position = Vector2(68,750)
    joy_base.size = Vector2(230,230)
    joy_base.mouse_filter = Control.MOUSE_FILTER_IGNORE
    hud.add_child(joy_base)
    var outer := Panel.new()
    outer.position = Vector2(12,12)
    outer.size = Vector2(206,206)
    outer.add_theme_stylebox_override("panel", _style(Color(0.08,0.11,0.12,0.26),Color(0.75,0.86,0.9,0.55),3,103))
    outer.mouse_filter = Control.MOUSE_FILTER_IGNORE
    joy_base.add_child(outer)
    joy_knob = Panel.new()
    joy_knob.position = Vector2(78,78)
    joy_knob.size = Vector2(74,74)
    joy_knob.add_theme_stylebox_override("panel", _style(Color(0.65,0.82,0.88,0.42),Color(0.9,0.97,1,0.75),2,37))
    joy_knob.mouse_filter = Control.MOUSE_FILTER_IGNORE
    joy_base.add_child(joy_knob)

func start_match() -> void:
    menu.visible = false
    if not OS.has_feature("mobile"):
        Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    _set_match_ui(true)
    match_active = true
    round_number = 1
    score_cats = 0
    score_dogs = 0
    _start_round()

func _set_match_ui(v:bool) -> void:
    hud.visible = v

func _start_round() -> void:
    round_ending = false
    c4_planted = false
    bomb_time = 35.0
    round_time = 100.0
    player_alive = true
    player_hp = 100.0
    armor = 100.0
    ammo = 30
    reserve = 90
    reloading = false
    firing = false
    player.visible = true
    player.position = Vector3(-23,0,-22) if player_team == 0 else Vector3(23,0,22)
    yaw = deg_to_rad(-45.0) if player_team == 0 else deg_to_rad(135.0)
    pitch = 0.0
    player.rotation.y = yaw
    camera.rotation.x = pitch
    for b in bots:
        if is_instance_valid(b):
            b.queue_free()
    bots.clear()
    await get_tree().process_frame
    _spawn_teams()
    banner_label.text = "ОПЕРАЦИЯ НАЧАЛАСЬ"
    banner_label.visible = true
    var tw := create_tween()
    tw.tween_interval(1.5)
    tw.tween_property(banner_label,"modulate:a",0.0,0.5)
    tw.tween_callback(func(): banner_label.visible=false; banner_label.modulate.a=1.0)
    _update_hud()

func _spawn_teams() -> void:
    var cat_spawns = [Vector3(-21,0,-22),Vector3(-24,0,-18),Vector3(-18,0,-24),Vector3(-16,0,-20),Vector3(-22,0,-15)]
    var dog_spawns = [Vector3(21,0,22),Vector3(24,0,18),Vector3(18,0,24),Vector3(16,0,20),Vector3(22,0,15)]
    for team in [0,1]:
        var spawns = cat_spawns if team == 0 else dog_spawns
        var created := 0
        for i in range(5):
            if team == player_team and i == player_variant % 5:
                continue
            if team == player_team and created >= 4:
                break
            var b := CharacterBody3D.new()
            b.set_script(BOT_SCRIPT)
            add_child(b)
            b.setup(self,team,i,spawns[i])
            bots.append(b)
            created += 1

func _physics_process(delta:float) -> void:
    if not match_active:
        return
    fire_cd = maxf(0.0,fire_cd-delta)
    if player_alive and not round_ending:
        _move_player(delta)
        if firing and not reloading and fire_cd <= 0.0:
            _shoot()
        _update_c4_state(delta)
    if not round_ending:
        if c4_planted:
            bomb_time -= delta
            if bomb_time <= 0.0:
                _finish_round(0,"C4 ВЗОРВАНА")
        else:
            round_time -= delta
            if round_time <= 0.0:
                _finish_round(1,"ВРЕМЯ ВЫШЛО")
    _update_hud()

func _move_player(delta:float) -> void:
    var kb := Vector2(float(Input.is_key_pressed(KEY_D)) - float(Input.is_key_pressed(KEY_A)), float(Input.is_key_pressed(KEY_S)) - float(Input.is_key_pressed(KEY_W)))
    var input_vec := joy_vec if joy_vec.length() > 0.05 else kb
    var local := Vector3(input_vec.x,0,input_vec.y)
    var dir := (Basis(Vector3.UP,yaw) * local).normalized()
    var speed := 4.8 if crouched else 6.1
    if aiming:
        speed *= 0.72
    player.velocity.x = dir.x * speed
    player.velocity.z = dir.z * speed
    if not player.is_on_floor():
        player.velocity.y -= 22.0*delta
    else:
        player.velocity.y = 0.0
    player.move_and_slide()
    var target_y := 1.18 if crouched else 1.62
    camera.position.y = lerpf(camera.position.y,target_y,delta*9.0)
    weapon_root.position.y = lerpf(weapon_root.position.y,-0.32 if aiming else -0.42,delta*10.0)
    weapon_root.position.x = lerpf(weapon_root.position.x,0.10 if aiming else 0.42,delta*10.0)

func _unhandled_input(event:InputEvent) -> void:
    if not match_active or not player_alive:
        return
    var vp := get_viewport().get_visible_rect().size
    if event is InputEventScreenTouch:
        if event.pressed:
            if event.position.x < vp.x*0.42 and event.position.y > vp.y*0.48 and left_touch == -1:
                left_touch = event.index
                joy_origin = event.position
                joy_pos = event.position
                _update_joy_visual()
            elif event.position.x > vp.x*0.38 and look_touch == -1:
                look_touch = event.index
        else:
            if event.index == left_touch:
                left_touch = -1
                joy_vec = Vector2.ZERO
                joy_knob.position = Vector2(78,78)
            if event.index == look_touch:
                look_touch = -1
    elif event is InputEventScreenDrag:
        if event.index == left_touch:
            joy_pos = event.position
            var d := joy_pos - joy_origin
            joy_vec = d.limit_length(joy_radius) / joy_radius
            _update_joy_visual()
        elif event.index == look_touch:
            _look_delta(event.relative * 0.0041)
    elif event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        _look_delta(event.relative * 0.0022)
    elif event is InputEventKey and event.pressed and event.physical_keycode == KEY_ESCAPE:
        Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _update_joy_visual() -> void:
    var d := (joy_pos-joy_origin).limit_length(joy_radius)
    joy_knob.position = Vector2(78,78) + d * 0.58

func _look_delta(d:Vector2) -> void:
    yaw -= d.x
    pitch = clampf(pitch-d.y,deg_to_rad(-72),deg_to_rad(72))
    player.rotation.y = yaw
    camera.rotation.x = pitch

func _shoot() -> void:
    if ammo <= 0:
        _reload()
        return
    ammo -= 1
    fire_cd = fire_delay
    muzzle_light.light_energy = 6.0
    var tw := create_tween()
    tw.tween_property(muzzle_light,"light_energy",0.0,0.055)
    weapon_root.position.z += 0.045
    var recoil := create_tween()
    recoil.tween_property(weapon_root,"position:z",-0.92,0.08)
    pitch = clampf(pitch + rng.randf_range(0.002,0.008),deg_to_rad(-72),deg_to_rad(72))
    camera.rotation.x = pitch

    var from := camera.global_position
    var to := from + (-camera.global_transform.basis.z * 120.0)
    var q := PhysicsRayQueryParameters3D.create(from,to)
    q.collision_mask = 3
    q.exclude = [player.get_rid()]
    var hit := get_world_3d().direct_space_state.intersect_ray(q)
    var endpoint := to
    if not hit.is_empty():
        endpoint = hit.position
        var c = hit.collider
        if c != null and c.has_method("take_damage") and c.team != player_team:
            c.take_damage(rng.randf_range(24.0,34.0),player)
    spawn_tracer(from + (-camera.global_transform.basis.z*0.8),endpoint,player_team)

func _reload() -> void:
    if reloading or ammo >= mag_size or reserve <= 0 or not player_alive:
        return
    reloading = true
    status_label.text = "ПЕРЕЗАРЯДКА..."
    var tw := create_tween()
    tw.tween_property(weapon_root,"rotation_degrees:z",-28.0,0.35)
    tw.tween_interval(0.65)
    tw.tween_property(weapon_root,"rotation_degrees:z",0.0,0.35)
    tw.tween_callback(_finish_reload)

func _finish_reload() -> void:
    var need := mag_size-ammo
    var got := mini(need,reserve)
    ammo += got
    reserve -= got
    reloading = false
    status_label.text = "M4A1"

func _toggle_aim() -> void:
    aiming = not aiming
    camera.fov = 55.0 if aiming else 78.0

func _toggle_crouch() -> void:
    crouched = not crouched

func _throw_grenade() -> void:
    if not player_alive:
        return
    var p := camera.global_position + (-camera.global_transform.basis.z * 6.0)
    p.y = maxf(0.8,p.y-0.7)
    var smoke := MeshInstance3D.new()
    var sphere := SphereMesh.new()
    sphere.radius = 1.0
    sphere.height = 2.0
    smoke.mesh = sphere
    smoke.position = p
    smoke.scale = Vector3.ONE*0.15
    smoke.material_override = make_mat(Color("aeb8b6"),0.0,1.0,0.50)
    add_child(smoke)
    var tw := create_tween()
    tw.tween_property(smoke,"scale",Vector3.ONE*5.5,1.2).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
    tw.tween_interval(4.5)
    tw.tween_property(smoke,"scale",Vector3.ONE*6.5,1.0)
    tw.parallel().tween_property(smoke,"modulate:a",0.0,1.0)
    tw.tween_callback(smoke.queue_free)

func _plant_or_defuse() -> void:
    if round_ending or not player_alive:
        return
    if player_team == 0 and not c4_planted:
        var a := player.global_position.distance_to(Vector3(-14,0,-14))
        var b := player.global_position.distance_to(Vector3(14,0,14))
        if minf(a,b) < 4.2:
            planted_site = Vector3(-14,0,-14) if a < b else Vector3(14,0,14)
            c4_planted = true
            bomb_time = 35.0
            banner_label.text = "C4 УСТАНОВЛЕНА"
            banner_label.visible = true
    elif player_team == 1 and c4_planted and player.global_position.distance_to(planted_site) < 4.0:
        _finish_round(1,"C4 ОБЕЗВРЕЖЕНА")

func _update_c4_state(_delta:float) -> void:
    plant_button.visible = (player_team == 0 and not c4_planted and (player.global_position.distance_to(Vector3(-14,0,-14)) < 5.5 or player.global_position.distance_to(Vector3(14,0,14)) < 5.5)) or (player_team == 1 and c4_planted and player.global_position.distance_to(planted_site) < 5.5)
    if not c4_planted:
        for b in bots:
            if is_instance_valid(b) and b.alive and b.team == 0:
                var da:float = b.global_position.distance_to(Vector3(-14,0,-14))
                var db:float = b.global_position.distance_to(Vector3(14,0,14))
                if minf(da,db) < 2.8 and rng.randf() < 0.003:
                    planted_site = Vector3(-14,0,-14) if da < db else Vector3(14,0,14)
                    c4_planted = true
                    bomb_time = 35.0
                    banner_label.text = "C4 УСТАНОВЛЕНА БОТОМ"
                    banner_label.visible = true
                    break
    if c4_planted and player_team == 1:
        for b in bots:
            if is_instance_valid(b) and b.alive and b.team == 1 and b.global_position.distance_to(planted_site) < 2.6 and rng.randf() < 0.0015:
                _finish_round(1,"БОТ ОБЕЗВРЕДИЛ C4")
                break

func get_bot_target(bot):
    var best = null
    var best_d := 9999.0
    for other in bots:
        if not is_instance_valid(other) or other == bot or not other.alive or other.team == bot.team:
            continue
        var d:float = bot.global_position.distance_to(other.global_position)
        if d < best_d:
            best_d = d
            best = other
    return best

func damage_player(amount:float, attacker=null) -> void:
    if not player_alive or round_ending:
        return
    var absorbed := minf(armor,amount*0.45)
    armor -= absorbed
    player_hp -= amount-absorbed*0.35
    _damage_flash()
    if player_hp <= 0.0:
        player_hp = 0.0
        player_alive = false
        player.visible = false
        banner_label.text = "ВЫ ВЫБЫЛИ — БОТЫ ПРОДОЛЖАЮТ"
        banner_label.visible = true
        _check_team_elimination()

func _damage_flash() -> void:
    var flash := ColorRect.new()
    flash.color = Color(0.8,0.02,0.02,0.18)
    flash.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
    hud.add_child(flash)
    var tw := create_tween()
    tw.tween_property(flash,"modulate:a",0.0,0.25)
    tw.tween_callback(flash.queue_free)

func bot_died(_bot, _attacker=null) -> void:
    _check_team_elimination()

func _check_team_elimination() -> void:
    if round_ending:
        return
    var cats := 1 if player_team == 0 and player_alive else 0
    var dogs := 1 if player_team == 1 and player_alive else 0
    for b in bots:
        if is_instance_valid(b) and b.alive:
            if b.team == 0: cats += 1
            else: dogs += 1
    if cats <= 0:
        _finish_round(1,"СОБАКИ ПОБЕДИЛИ")
    elif dogs <= 0:
        _finish_round(0,"КОТЫ ПОБЕДИЛИ")

func _finish_round(winner:int, reason:String) -> void:
    if round_ending:
        return
    round_ending = true
    firing = false
    if winner == 0: score_cats += 1
    else: score_dogs += 1
    banner_label.text = reason
    banner_label.modulate.a = 1.0
    banner_label.visible = true
    if score_cats >= 6 or score_dogs >= 6:
        match_active = false
        await get_tree().create_timer(2.2).timeout
        _show_match_result()
    else:
        await get_tree().create_timer(2.2).timeout
        round_number += 1
        _start_round()

func _show_match_result() -> void:
    _set_match_ui(false)
    menu.visible = true
    var winner := "КОТЫ" if score_cats > score_dogs else "СОБАКИ"
    var result := Label.new()
    result.text = "ПОБЕДА: %s   %d : %d" % [winner,score_cats,score_dogs]
    result.position = Vector2(560,265)
    result.size = Vector2(800,70)
    result.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    result.add_theme_font_size_override("font_size",34)
    result.add_theme_color_override("font_color",Color("ffd26a"))
    menu.add_child(result)
    var tw := create_tween()
    tw.tween_interval(5.0)
    tw.tween_callback(result.queue_free)

func spawn_tracer(from:Vector3, to:Vector3, team:int) -> void:
    var dist := from.distance_to(to)
    if dist <= 0.05:
        return
    var tr := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = Vector3(0.025,0.025,dist)
    tr.mesh = bm
    tr.position = (from+to)*0.5
    tr.look_at(to,Vector3.UP)
    tr.material_override = make_mat(Color("77d3ff") if team == 0 else Color("ff765f"),0.0,0.2,0.82)
    add_child(tr)
    var tw := create_tween()
    tw.tween_interval(0.055)
    tw.tween_callback(tr.queue_free)

func spawn_hit(pos:Vector3, team:int) -> void:
    var spark := MeshInstance3D.new()
    var sm := SphereMesh.new()
    sm.radius = 0.12
    sm.height = 0.24
    spark.mesh = sm
    spark.position = pos
    spark.material_override = make_mat(Color("8de3ff") if team == 0 else Color("ff9a72"),0.0,0.25)
    add_child(spark)
    var light := OmniLight3D.new()
    light.light_color = Color("67d5ff") if team == 0 else Color("ff7b50")
    light.light_energy = 3.0
    light.omni_range = 2.5
    spark.add_child(light)
    var tw := create_tween()
    tw.tween_property(spark,"scale",Vector3.ONE*2.2,0.10)
    tw.tween_property(spark,"scale",Vector3.ZERO,0.16)
    tw.tween_callback(spark.queue_free)

func _update_hud() -> void:
    if not hud.visible:
        return
    score_label.text = "%d       %d" % [score_cats,score_dogs]
    if c4_planted:
        timer_label.text = "C4  %02d" % maxi(0,int(ceil(bomb_time)))
        timer_label.add_theme_color_override("font_color",Color("ff665e"))
    else:
        var t := maxi(0,int(ceil(round_time)))
        timer_label.text = "%02d:%02d" % [t/60,t%60]
        timer_label.add_theme_color_override("font_color",Color("dcecf2"))
    ammo_label.text = "%d / %d" % [ammo,reserve]
    hp_label.text = "✚ %d" % int(player_hp)
    armor_label.text = "◆ %d" % int(armor)
    money_label.text = "$ %d" % money
