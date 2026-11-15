#!/usr/bin/env python3
"""Aurora v0.7: repairs third-person locomotion, winter map and animated snow compression.

Run on v0.6 full source. The cloud CI performs v0.5 -> v0.6 -> v0.7 in sequence.
"""
import sys
from pathlib import Path
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/mnt/data/aurora_v07_src')

def patch(rel, before, after):
    path=root/rel
    value=path.read_text()
    if before not in value:
        raise RuntimeError(f'Expected anchor not found in {rel}: {before[:125]}')
    path.write_text(value.replace(before,after,1))

# Reliable touch joystick: independent of the camera input and responsive while dragging.
(root/'scripts/joystick.gd').write_text('''extends Control

# Persistent fixed virtual stick, tracked independently from the right-hand camera finger.
var direction := Vector2.ZERO
var held_id := -1
var knob_offset := Vector2.ZERO
var pad_radius := 81.0
var center := Vector2.ZERO

func _ready() -> void:
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    set_process_input(true)
    _sync_center()

func _sync_center() -> void:
    var size_ := get_viewport_rect().size
    center = Vector2(clampf(size_.x * 0.12, 98.0, 155.0), size_.y - clampf(size_.y * 0.16, 102.0, 154.0))

func reset() -> void:
    held_id = -1
    direction = Vector2.ZERO
    knob_offset = Vector2.ZERO
    queue_redraw()

func _input(event: InputEvent) -> void:
    _sync_center()
    var size_ := get_viewport_rect().size
    if event is InputEventScreenTouch:
        if event.pressed and held_id == -1 and event.position.x < size_.x * .43 and event.position.y > size_.y * .49:
            held_id = event.index
            _update_direction(event.position)
        elif not event.pressed and event.index == held_id:
            reset()
    elif event is InputEventScreenDrag and held_id >= 0 and event.index == held_id:
        _update_direction(event.position)
    elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
        if event.pressed and held_id == -1 and event.position.x < size_.x * .43 and event.position.y > size_.y * .49:
            held_id = 99
            _update_direction(event.position)
        elif not event.pressed and held_id == 99:
            reset()
    elif event is InputEventMouseMotion and held_id == 99 and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
        _update_direction(event.position)

func _update_direction(point: Vector2) -> void:
    knob_offset = (point - center).limit_length(pad_radius)
    direction = knob_offset / pad_radius
    if direction.length() < 0.12:
        direction = Vector2.ZERO
    queue_redraw()

func _draw() -> void:
    _sync_center()
    draw_circle(center, 97.0, Color(.04, .105, .16, .57))
    draw_arc(center, 97.0, 0, TAU, 80, Color(.86, .96, 1.0, .44), 3.0, true)
    draw_circle(center, 82.0, Color(.1, .21, .27, .27))
    draw_circle(center + knob_offset, 38.0, Color(.45, .72, .91, .86))
    draw_arc(center + knob_offset, 38.0, 0, TAU, 40, Color(.91, .98, 1.0, .93), 2.5, true)
''')

# Better integration with Godot's imported KayKit 3D animation clips and game movement.
patch('scripts/player.gd',
    '    move_vec = move_vec.limit_length(1.0)\n    var direction',
    '    move_vec = move_vec.limit_length(1.0)\n    var direction')
patch('scripts/player.gd',
    '    var direction := Basis(Vector3.UP, camera_yaw) * Vector3(move_vec.x, 0, move_vec.y)',
    '    var direction := Basis(Vector3.UP, camera_yaw) * Vector3(move_vec.x, 0, move_vec.y)\n    # Do not allow residual velocity to mask an unresponsive touch stick.\n    # Movement comes from both Android touch and desktop keyboard.\n    if direction.length_squared() > 1.0:\n        direction = direction.normalized()')
patch('scripts/player.gd',
    '    _update_camera_obstruction()\n    var speed_ratio',
    '    _update_camera_obstruction()\n    var speed_ratio')
patch('scripts/player.gd',
    '    cam.look_at(global_position + Vector3(0, 1.5, 0), Vector3.UP)\n    camera_target',
    '    cam.look_at(global_position + Vector3(0, 1.5, 0), Vector3.UP)\n    camera_target')
patch('scripts/player.gd',
    '    if direction.length_squared() > 0.01:\n        var wanted',
    '    if direction.length_squared() > 0.01:\n        var wanted')
# Make cloth update less expensive; main CPU bottleneck on slower Android phones.
patch('scripts/player.gd', 'var current_clip: StringName = &""',
'''var current_clip: StringName = &""
var cape_update_time := 0.0''')
patch('scripts/player.gd',
    '    _update_cape(float(Time.get_ticks_msec()) * 0.001, speed_ratio)',
    '''    cape_update_time += delta
    if cape_update_time > 0.09:
        cape_update_time = 0.0
        _update_cape(float(Time.get_ticks_msec()) * 0.001, speed_ratio)''')
patch('scripts/player.gd',
    '    floor_snap_length = 0.45',
    '''    # 3D player capsule is kept clear of the floor; reduces initial ground penetration.
    floor_snap_length = 0.45''')

# Winter snow has a denser drivable trail, more landmark visibility, safe spawn areas.
patch('scripts/world.gd',
    'var rng := RandomNumberGenerator.new()',
    '''var rng := RandomNumberGenerator.new()
var snow_image: Image
var snow_texture: ImageTexture
var snow_dirty := false
var snow_upload_timer := 0.0
const SNOW_WIDTH := 180.0
const SNOW_IMAGE_SIZE := 1024''')
patch('scripts/world.gd',
    '    biome = target\n    rng.seed = 1849',
    '''    biome = target
    snow_image = null
    snow_texture = null
    snow_dirty = false
    if biome == "winter":
        snow_image = Image.create(SNOW_IMAGE_SIZE, SNOW_IMAGE_SIZE, false, Image.FORMAT_L8)
        snow_image.fill(Color.BLACK)
        snow_texture = ImageTexture.create_from_image(snow_image)
    rng.seed = 1849''')
patch('scripts/world.gd',
    '    var steps := 112 if biome != "cabin" else 8\n    var half := width_ * 0.5\n    for z_idx in range(steps):\n        for x_idx in range(steps):\n            var x0 := -half + width_ * float(x_idx) / float(steps)\n            var x1 := -half + width_ * float(x_idx + 1) / float(steps)\n            var z0 := -half + width_ * float(z_idx) / float(steps)\n            var z1 := -half + width_ * float(z_idx + 1) / float(steps)',
    '''    # High-resolution winter walking corridor is surrounded by cheaper terrain.
    # One ArrayMesh, no visible seam between strips, accurate local snow depression.
    var stripes := [Vector3(-90.0, 90.0, 112.0)]
    if biome == "winter":
        stripes = [Vector3(-90.0, -12.0, 45.0), Vector3(-12.0, 12.0, 92.0), Vector3(12.0, 90.0, 45.0)]
    var z_steps := 110 if biome != "winter" else 260
    for strip in stripes:
        var x_steps := int(strip.z)
        for z_idx in range(z_steps):
            for x_idx in range(x_steps):
                var x0 := lerpf(strip.x, strip.y, float(x_idx) / x_steps)
                var x1 := lerpf(strip.x, strip.y, float(x_idx + 1) / x_steps)
                var z0 := lerpf(-width_ * 0.5, width_ * 0.5, float(z_idx) / z_steps)
                var z1 := lerpf(-width_ * 0.5, width_ * 0.5, float(z_idx + 1) / z_steps)''')
# Above rewrites indentation; need shift entire original triangle assembly indent one level.
path=root/'scripts/world.gd'
s=path.read_text()
start=s.index('            var p0 := Vector3(x0, _terrain_height')
end=s.index('    surface.generate_normals()', start)
block=s[start:end]
# Source p0... was indented 12 spaces in initial 2 nested loops; now needs 16.
# Bump lines starting with 12 spaces by 4, but preserve already 16 and 20 inside arrays.
s=s[:start]+''.join(('    '+line if line.strip() else line) for line in block.splitlines(keepends=True))+s[end:]
path.write_text(s)

patch('scripts/world.gd',
    '''        terrain_material.shader = preload("res://shaders/terrain_blend.gdshader")
        terrain_material.set_shader_parameter("ground_tex", texture_)
        terrain_material.set_shader_parameter("trail_tex", SNOW_TEX if biome == "winter" else PATH_TEX)
        terrain_material.set_shader_parameter("winter", biome == "winter")''',
    '''        if biome == "winter":
            terrain_material.shader = preload("res://shaders/snow_tracks.gdshader")
            terrain_material.set_shader_parameter("footprint_map", snow_texture)
            terrain_material.set_shader_parameter("snow_world_size", SNOW_WIDTH)
        else:
            terrain_material.shader = preload("res://shaders/terrain_blend.gdshader")
            terrain_material.set_shader_parameter("winter", false)
        terrain_material.set_shader_parameter("ground_tex", texture_)
        terrain_material.set_shader_parameter("trail_tex", SNOW_TEX if biome == "winter" else PATH_TEX)''')
patch('scripts/world.gd',
    '''        if absf(x - path_x) < 4.0 and z < 3.0:
            x += 6.5 if x >= 0 else -6.5
        if absf(x) < 5.0 and absf(z) < 5.0:
            x += 6.0''',
    '''        # Keep the entire route AND the starting zone clear of tree colliders.
        if absf(x - path_x) < 7.5 or (absf(x) < 8.5 and z > 2.0 and z < 18.0):
            x += 10.0 if x >= path_x else -10.0''')
patch('scripts/world.gd',
    '''        if absf(x - path_x) < 4.3 and z < 3.0:
            x += 6.5 if x >= 0 else -6.5
        if absf(x) < 8 and z < -39 and z > -57:
            x += 11.0''',
    '''        # Snow trail to cabin and player spawn are both safe to walk through.
        if absf(x - path_x) < 7.5 or (absf(x) < 8.0 and z > 2.0 and z < 18.0):
            x += 11.0 if x >= path_x else -11.0
        if absf(x) < 8.0 and z < -39 and z > -57:
            x += 11.0''')
patch('scripts/world.gd',
    '    _make_aurora()\n    _particles(true)',
    '    _make_aurora()\n    _particles(true)\n    _winter_waymarkers()')

with (root/'scripts/world.gd').open('a') as f:
    f.write('''

# Stable, persistent footprint heightmap. Updated in small circles on walking steps.
# Both vertex height and surface albedo use this texture, so snow is visibly compressed.
func stamp_snow(where: Vector3, side: float = 0.0) -> void:
    if biome != "winter" or snow_image == null:
        return
    var texel := SNOW_IMAGE_SIZE / SNOW_WIDTH
    var xx := int((where.x + SNOW_WIDTH * .5) * texel)
    var zz := int((where.z + SNOW_WIDTH * .5) * texel)
    var radius_px := 4
    for dz in range(-radius_px, radius_px + 1):
        for dx in range(-radius_px, radius_px + 1):
            var u := xx + dx
            var v := zz + dz
            if u < 0 or v < 0 or u >= SNOW_IMAGE_SIZE or v >= SNOW_IMAGE_SIZE:
                continue
            var elliptical := sqrt(pow(float(dx) / (3.0 + absf(side)), 2.0) + pow(float(dz) / 4.2, 2.0))
            if elliptical >= 1.0:
                continue
            var compression := pow(1.0 - elliptical, 0.62)
            var previous := snow_image.get_pixel(u, v).r
            snow_image.set_pixel(u, v, Color(maxf(previous, compression), 0, 0, 1))
            snow_dirty = true

func _process(delta: float) -> void:
    if snow_dirty and snow_texture != null:
        snow_upload_timer += delta
        if snow_upload_timer >= 0.12:
            snow_texture.update(snow_image)
            snow_dirty = false
            snow_upload_timer = 0.0

func _winter_waymarkers() -> void:
    # Readable scenery and route markers: the winter map is not a blank plain.
    var timber := _material(Color("4C6268"))
    var teal := _material(Color("68DCC7"))
    teal.emission_enabled = true
    teal.emission = Color("44F0C4")
    teal.emission_energy_multiplier = 1.1
    for i in range(15):
        var z := 6.0 - i * 3.7
        var x := sin(-z * .085) * 1.6
        for side in [-1.0, 1.0]:
            var base := Vector3(x + side * 5.1, _terrain_height(x + side * 5.1, z), z)
            var stick := _box(base + Vector3(0, 0.65, 0), Vector3(.16, 1.3, .16), timber)
            var tip := MeshInstance3D.new()
            var tetra := SphereMesh.new()
            tetra.radius = .2
            tetra.height = .35
            tip.mesh = tetra
            tip.material_override = teal
            tip.position = base + Vector3(0, 1.44, 0)
            add_child(tip)
    # Three snow-covered boulders on either side of the path make it navigable.
    for z in [-10.0, -29.0, -42.0]:
        for side in [-1.0, 1.0]:
            _model(_nature_scene("Rock_Medium_2", ICE_ROCK), Vector3(side * 9.2, .05, z), 1.7)
''')

# Shader uses a 1024 x 1024 dynamic image updated only after an actual step.
(root/'shaders/snow_tracks.gdshader').write_text('''shader_type spatial;
render_mode cull_back, diffuse_burley, specular_disabled;
uniform sampler2D ground_tex : source_color, repeat_enable, filter_linear_mipmap;
uniform sampler2D trail_tex : source_color, repeat_enable, filter_linear_mipmap;
uniform sampler2D footprint_map : filter_linear, repeat_disable;
uniform float snow_world_size = 180.0;
varying vec2 snow_uv;
varying float path_mask;

void vertex() {
    path_mask = COLOR.r;
    snow_uv = VERTEX.xz / snow_world_size + vec2(0.5);
    float pressed = textureLod(footprint_map, snow_uv, 0.0).r;
    VERTEX.y -= pressed * 0.105;
}

void fragment() {
    float pressed = texture(footprint_map, snow_uv).r;
    vec3 base_snow = texture(ground_tex, UV).rgb;
    vec3 trail_snow = texture(trail_tex, UV * 0.85).rgb;
    float trail = smoothstep(0.02, 0.96, path_mask);
    float tiny_noise = sin(UV.x * 46.0) * sin(UV.y * 51.0) * 0.016;
    vec3 snow = mix(base_snow, trail_snow * vec3(0.88, 0.96, 1.02), trail * 0.55);
    // Compact snow in the footprint darkens slightly, with cold blue shading.
    snow *= (1.0 - pressed * 0.25 + tiny_noise);
    ALBEDO = clamp(snow * mix(vec3(0.97, 1.04, 1.11), vec3(0.75, 0.89, 1.02), pressed * 0.36), vec3(0.0), vec3(1.0));
    ROUGHNESS = mix(0.95, 0.78, pressed);
}
''')

# The winter level gets an actual navigable in-game map, updated to show the player.
(root/'scripts/minimap.gd').write_text('''extends Control

var game: Variant
var hero: Variant

func _ready() -> void:
    mouse_filter = Control.MOUSE_FILTER_IGNORE

func _process(_delta: float) -> void:
    if visible:
        queue_redraw()

func _draw() -> void:
    var rect := Rect2(Vector2.ZERO, size)
    draw_rect(rect, Color(.025, .075, .12, .87), true)
    draw_rect(rect.grow(-1), Color(.46, .85, .89, .73), false, 2.0)
    if game == null or hero == null:
        return
    var winter: bool = game.world.biome == "winter"
    var tint := Color(.62, .79, .86) if winter else Color(.55, .67, .30)
    draw_rect(Rect2(Vector2(8, 8), size - Vector2(16, 16)), tint.darkened(.5), true)
    var points := PackedVector2Array()
    for idx in range(51):
        var z := lerpf(22.0, -62.0, float(idx) / 50.0)
        var x := sin(-z * .085) * (1.6 if winter else 2.9)
        points.append(_loc(x, z))
    draw_polyline(points, Color(.80, .91, .95, .74) if winter else Color(.91, .74, .42), 4.5, true)
    var dots := [-54.0, -46.0, -31.0, -17.0, -5.0, 12.0]
    for z in dots:
        for side in [-1.0, 1.0]:
            draw_circle(_loc(side * 13.0, z), 3.0, Color(.27, .52, .55) if winter else Color(.44, .63, .25))
    var destination := Vector2(0, -47) if winter else Vector2(0, -45)
    draw_circle(_loc(destination.x, destination.y), 6.4, Color(.95, .78, .38))
    var pointer := _loc(hero.global_position.x, hero.global_position.z)
    draw_circle(pointer, 6.6, Color(.04, .11, .17))
    draw_circle(pointer, 4.3, Color(.98, .99, .98))
    var head := Vector2(sin(hero.camera_yaw), -cos(hero.camera_yaw))
    draw_line(pointer, pointer + head * 11.0, Color.WHITE, 2.0, true)
    draw_string(ThemeDB.fallback_font, Vector2(14, 22), "СНЕЖНЫЙ ПУТЬ" if winter else "ТРОПА", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color.WHITE)

func _loc(x: float, z: float) -> Vector2:
    return Vector2(size.x * 0.5 + x / 70.0 * (size.x * .42), size.y * .79 - (13.0 - z) / 86.0 * (size.y * .66))
''')

# HUD map toggle; joystick stays visible when menu closes; note reset on scene change.
patch('scripts/hud.gd', 'var menu_button: Button\n', 'var menu_button: Button\nvar map_button: Button\nvar minimap: Variant\n')
patch('scripts/hud.gd',
'''    overlay.add_child(joystick)
    title_label''',
'''    overlay.add_child(joystick)
    minimap = load("res://scripts/minimap.gd").new()
    minimap.name = "WinterRouteMap"
    minimap.size = Vector2(238.0, 184.0)
    minimap.game = game
    minimap.hero = hero
    minimap.visible = false
    overlay.add_child(minimap)
    title_label''')
patch('scripts/hud.gd',
'''    overlay.add_child(worlds_button)
    menu_button''',
'''    overlay.add_child(worlds_button)
    map_button = _style_button("КАРТА", Color(0.08, 0.25, 0.32, 0.85), 16)
    map_button.pressed.connect(func(): minimap.visible = not minimap.visible)
    overlay.add_child(map_button)
    menu_button''')
patch('scripts/hud.gd',
'''    worlds_button.position = Vector2(w - 223, 20)
    worlds_button.size''',
'''    map_button.position = Vector2(w - 330, 20)
    map_button.size = Vector2(97, 48)
    minimap.position = Vector2(w - 270, 80)
    worlds_button.position = Vector2(w - 223, 20)
    worlds_button.size''')
patch('scripts/hud.gd',
    '    worlds_button.visible = not show_\n',
    '    worlds_button.visible = not show_\n    map_button.visible = not show_\n    minimap.visible = false\n')
patch('scripts/hud.gd',
'''    if joystick != null:
        joystick.direction = Vector2.ZERO
        joystick.knob_offset = Vector2.ZERO
        joystick.queue_redraw()''',
'''    if joystick != null:
        joystick.reset()''')
patch('scripts/hud.gd',
'''    chooser.visible = false

func _input(event: InputEvent)''',
'''    chooser.visible = false
    minimap.visible = game.world.biome == "winter" and not menu_open
    if joystick != null:
        joystick.reset()

func _input(event: InputEvent)''')

# Ensure scene swaps are entirely clear before teleporting, with safer spawn heights.
patch('scripts/main.gd',
    '    hero.teleport_to(Vector3(0, 0.4, 8))',
    '    hero.teleport_to(Vector3(0, 1.7, 8))')
patch('scripts/main.gd',
    'hero.teleport_to(Vector3(0, 0.4, 11.0))',
    'hero.teleport_to(Vector3(0, 1.7, 11.0))')
patch('scripts/main.gd',
    'hero.teleport_to(Vector3(0, 0.4, 5.0))',
    'hero.teleport_to(Vector3(0, 1.7, 5.0))')
patch('scripts/main.gd',
    'hero.teleport_to(Vector3(0, 0.4, 8.0))',
    'hero.teleport_to(Vector3(0, 1.7, 8.0))')
patch('scripts/main.gd',
    'var glowing_charms: Array[Node3D] = []',
    '''var glowing_charms: Array[Node3D] = []
var snow_step_distance := 0.0
var left_foot := false''')
patch('scripts/main.gd',
    '''    hud.notify_scene_changed()

func use_portal()''',
    '''    snow_step_distance = 0.0
    hud.notify_scene_changed()

func _physics_process(delta: float) -> void:
    if world.biome != "winter" or not hero.movement_enabled:
        return
    var horizontal := Vector2(hero.velocity.x, hero.velocity.z)
    var movement := horizontal.length()
    if not hero.is_on_floor() or movement < 0.8:
        return
    snow_step_distance += movement * delta
    if snow_step_distance > 0.53:
        snow_step_distance = 0.0
        left_foot = not left_foot
        var lateral := Vector3(cos(hero.look_node.rotation.y), 0.0, -sin(hero.look_node.rotation.y))
        var foot_pos: Vector3 = hero.global_position + lateral * (0.18 if left_foot else -0.18)
        world.stamp_snow(foot_pos, .25)

func use_portal()''')

# v0.2-v0.6 collision regression: invisible rescue ground blocked real movement.
patch('scripts/main.gd',
    '        fallback.visible = world.get_child_count() < 10',
    """        var fallback_required: bool = world.get_child_count() < 10
        fallback.visible = fallback_required
        var rescue_shape := fallback.get_node_or_null("SafetyGroundBody/SafetyGroundCollision") as CollisionShape3D
        if rescue_shape != null:
            rescue_shape.set_deferred("disabled", not fallback_required)""")
patch('scenes/main.tscn',
    """[node name="SafetyGroundCollision" type="CollisionShape3D" parent="FallbackEnvironment/SafetyGroundBody"]
position = Vector3(0, -0.34, 0)
shape = SubResource("RescueCollision")""",
    """[node name="SafetyGroundCollision" type="CollisionShape3D" parent="FallbackEnvironment/SafetyGroundBody"]
position = Vector3(0, -0.34, 0)
shape = SubResource("RescueCollision")
disabled = true""")

# Use stable broad-phase ground collision instead of terrain triangle soup.
# The dense visual terrain mesh remains intact for snow displacement and shaders.
# This avoids CharacterBody3D colliding with accidental side faces and getting stuck.
patch('scripts/world.gd',
    '''    var body := StaticBody3D.new()
    body.name = "TerrainCollision"
    var collider := CollisionShape3D.new()
    collider.shape = mesh.create_trimesh_shape()
    body.add_child(collider)
    add_child(body)''',
    '''    var body := StaticBody3D.new()
    body.name = "TerrainCollision"
    var collider := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(180.0, 2.0, 180.0)
    collider.shape = shape
    collider.position.y = -1.0
    body.add_child(collider)
    add_child(body)''')

patch('project.godot',
    'config/name="Aurora: Between Seasons — CC0 Remake v0.5"',
    'config/name="Aurora: Between Seasons — Snow Trails v0.7"')
patch('export_presets.cfg',
    'com.aurorabtw.seasons.visual06', 'com.aurorabtw.seasons.visual07')
patch('export_presets.cfg',
    'version/code=6', 'version/code=7')
patch('export_presets.cfg',
    'version/name="0.6"', 'version/name="0.7"')
patch('export_presets.cfg',
    'Aurora-v0.6-Android-debug.apk', 'Aurora-v0.7-Android-debug.apk')
(root/'README_V07.md').write_text('''# Aurora v0.7 - winter map + movement + snow compression

- Fixed Android virtual joystick handling, increased contact area, automatic reset when changing worlds
- Adjusted player spawn to avoid terrain clipping; cleared movement and spawn corridors of tree colliders
- Added actual in-game map on winter level, visible after scene change and toggleable through KARTA button
- Rebuilt winter ground mesh with extra vertices along path to support visible shader displacement
- Added dynamic shoe impressions recorded in a 1024x1024 L8 texture, fed to the snow shader, depressing snow by up to 0.105m and locally darkening compressed snow
- Added glowing trail waymarkers and route rocks; kept original CC0 models
- Reduced per-frame procedural cape mesh updates
- Preserves the original game mechanics (memories, biome travel, CC0 models)

This is a test build: Godot cloud test verifies project import, runtime exceptions and export. Real device testing remains necessary.\n''')
print('Applied Aurora v0.7 patch to', root)