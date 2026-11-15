#!/usr/bin/env python3
"""Aurora v0.6 visual polishing pass; safe to run on the v0.5 build output."""
from pathlib import Path
import sys
root = Path(sys.argv[1] if len(sys.argv) > 1 else '/mnt/data/aurora_v06_src')
world_path = root / 'scripts/world.gd'
player_path = root / 'scripts/player.gd'
hud_path = root / 'scripts/hud.gd'


def change(path, old, new):
    text = path.read_text()
    if old not in text:
        raise RuntimeError(f'{path}: expected anchor not found: {old[:80]}')
    path.write_text(text.replace(old, new, 1))

change(world_path,
       '_scatter_ground(true)\n    _add_grass_bed(true)\n    _sunbeams()',
       '_scatter_ground(true)\n    _add_grass_bed(true)\n    _v06_autumn_undergrowth()\n    _v06_woodland_details()\n    _sunbeams()')
change(world_path,
       '_build_mountains()\n    _add_grass_bed(false)',
       '_build_mountains()\n    _add_grass_bed(false)\n    _v06_snowbanks()')
change(world_path,
       '    action_position = Vector3(0, 0, 6.4)\n    action_caption',
       '    _v06_cabin_lamps()\n    action_position = Vector3(0, 0, 6.4)\n    action_caption')
change(world_path,
       '_environment(Color("6F9CB4"), Color("F3D59F"), Color("A18D69"), 0.014, 2.0)',
       '_environment(Color("7FADC6"), Color("FFE0A3"), Color("C2A482"), 0.009, 2.15)')

with world_path.open('a') as out:
    out.write('''

# v0.6: Additional scene detail is batched into MultiMeshes to keep Android draw calls low.
# Organic woodland floor vegetation; skips the walking trail and the spawn zone.
func _v06_autumn_undergrowth() -> void:
    var detail_rng := RandomNumberGenerator.new()
    detail_rng.seed = 610626
    var gltf: PackedScene = _nature_scene("Bush_Common", FERN)
    for i in range(135):
        var z := detail_rng.randf_range(-74.0, 31.0)
        var x := detail_rng.randf_range(-57.0, 57.0)
        var cx := sin(-z * 0.085) * 2.9
        if absf(x - cx) < 5.4:
            continue
        if absf(x) < 7.0 and absf(z) < 8.0:
            continue
        _model(gltf, Vector3(x, 0.03, z), detail_rng.randf_range(0.53, 1.38), detail_rng.randf_range(0.0, TAU))

    # Thin grass plumes create a softer silhouette in the foreground.
    var blade := QuadMesh.new()
    blade.size = Vector2(0.21, 0.68)
    var grass_mat := StandardMaterial3D.new()
    grass_mat.albedo_color = Color.WHITE
    grass_mat.vertex_color_use_as_albedo = true
    grass_mat.roughness = 0.98
    grass_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
    blade.material = grass_mat
    var multi := MultiMesh.new()
    multi.transform_format = MultiMesh.TRANSFORM_3D
    multi.use_colors = true
    multi.mesh = blade
    multi.instance_count = 2200
    for i in range(multi.instance_count):
        var z := detail_rng.randf_range(-59.0, 29.0)
        var x := detail_rng.randf_range(-47.0, 47.0)
        var cx := sin(-z * 0.085) * 2.9
        if absf(x - cx) < 4.8:
            x = cx + (5.2 if x > cx else -5.2)
        var h := detail_rng.randf_range(0.55, 1.55)
        var rot := Basis(Vector3.UP, detail_rng.randf_range(0.0, TAU)).scaled(Vector3(h, h, h))
        var p := Vector3(x, _terrain_height(x, z) + 0.33 * h, z)
        multi.set_instance_transform(i, Transform3D(rot, p))
        multi.set_instance_color(i, Color.from_hsv(detail_rng.randf_range(0.11, 0.18), 0.36, detail_rng.randf_range(0.47, 0.83)))
    var grass := MultiMeshInstance3D.new()
    grass.name = "AutumnGrassPlumesV06"
    grass.multimesh = multi
    grass.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    add_child(grass)

func _v06_woodland_details() -> void:
    var detail_rng := RandomNumberGenerator.new()
    detail_rng.seed = 601608
    var bark := _material(Color("6D503B"))
    var light_bark := _material(Color("9C8060"))
    var moss := _material(Color("536B3B"))
    for i in range(31):
        var z := detail_rng.randf_range(-73.0, 22.0)
        var x := detail_rng.randf_range(-49.0, 49.0)
        var center := sin(-z * 0.085) * 2.9
        if absf(x - center) < 6.1:
            continue
        var length := detail_rng.randf_range(1.8, 4.2)
        var branch := MeshInstance3D.new()
        var trunk := CylinderMesh.new()
        trunk.top_radius = 0.19
        trunk.bottom_radius = 0.29
        trunk.height = length
        trunk.radial_segments = 9
        branch.mesh = trunk
        branch.material_override = bark if i % 4 else light_bark
        branch.position = Vector3(x, _terrain_height(x, z) + 0.24, z)
        branch.rotation = Vector3(0.0, detail_rng.randf_range(-PI, PI), PI / 2.0 + detail_rng.randf_range(-0.2, 0.2))
        branch.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        add_child(branch)
        if i % 2 == 0:
            var patch := MeshInstance3D.new()
            var patch_mesh := SphereMesh.new()
            patch_mesh.radius = detail_rng.randf_range(0.36, 0.73)
            patch_mesh.height = 0.16
            patch.mesh = patch_mesh
            patch.material_override = moss
            patch.position = branch.position + Vector3(0.0, 0.05, 0.45)
            add_child(patch)

    # Motes in the shafts of sun: translucent, unlit, cheap CPU particle pass.
    var particles := CPUParticles3D.new()
    particles.name = "SunlitPollenV06"
    particles.amount = 85
    particles.lifetime = 6.5
    particles.preprocess = 6.5
    particles.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
    particles.emission_box_extents = Vector3(19.0, 4.0, 17.0)
    particles.position = Vector3(0.0, 4.0, -12.0)
    particles.direction = Vector3(-0.1, 0.3, 0.05)
    particles.gravity = Vector3(0.0, 0.025, 0.0)
    particles.initial_velocity_min = 0.035
    particles.initial_velocity_max = 0.15
    particles.scale_amount_min = 0.35
    particles.scale_amount_max = 0.95
    var mote := SphereMesh.new()
    mote.radius = 0.035
    mote.height = 0.07
    var mat := StandardMaterial3D.new()
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.albedo_color = Color(1.0, 0.75, 0.39, 0.56)
    mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    mote.material = mat
    particles.mesh = mote
    particles.emitting = true
    add_child(particles)

func _v06_snowbanks() -> void:
    var detail_rng := RandomNumberGenerator.new()
    detail_rng.seed = 602601
    var drift := SphereMesh.new()
    drift.radius = 1.0
    drift.height = 2.0
    drift.radial_segments = 12
    drift.rings = 6
    var mat := _material(Color.WHITE)
    mat.vertex_color_use_as_albedo = true
    drift.material = mat
    var mm := MultiMesh.new()
    mm.transform_format = MultiMesh.TRANSFORM_3D
    mm.use_colors = true
    mm.mesh = drift
    mm.instance_count = 170
    for i in range(mm.instance_count):
        var z := detail_rng.randf_range(-66.0, 23.0)
        var x := detail_rng.randf_range(-53.0, 53.0)
        var cx := sin(-z * 0.085) * 1.6
        if absf(x - cx) < 5.0:
            x = cx + (6.7 if x >= cx else -6.7)
        var width := detail_rng.randf_range(0.7, 2.3)
        var scale_ := Basis().scaled(Vector3(width, detail_rng.randf_range(0.18, 0.49), width * detail_rng.randf_range(0.8, 1.3)))
        mm.set_instance_transform(i, Transform3D(scale_, Vector3(x, _terrain_height(x, z) - 0.18, z)))
        mm.set_instance_color(i, Color("E4F0F1") if i % 3 else Color("AFCFD8"))
    var banks := MultiMeshInstance3D.new()
    banks.name = "SnowdriftClustersV06"
    banks.multimesh = mm
    banks.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    add_child(banks)

func _v06_cabin_lamps() -> void:
    for pos in [Vector3(-5.8, 3.8, -5.8), Vector3(6.1, 3.5, 4.4)]:
        var glow := OmniLight3D.new()
        glow.position = pos
        glow.light_color = Color("FFD199")
        glow.light_energy = 0.84
        glow.omni_range = 7.8
        glow.shadow_enabled = false
        add_child(glow)
        var lamp := MeshInstance3D.new()
        lamp.mesh = SphereMesh.new()
        lamp.scale = Vector3(0.24, 0.38, 0.24)
        lamp.position = pos
        var material := _material(Color("F9DB93"))
        material.emission_enabled = true
        material.emission = Color("FFB56D")
        material.emission_energy_multiplier = 1.8
        lamp.material_override = material
        add_child(lamp)
''')

change(player_path,
       '    cam.fov = 67.0',
       '    cam.fov = 65.0')
change(player_path,
       '    cam.look_at(focus, Vector3.UP)',
       '''    cam.look_at(focus, Vector3.UP)
    # Cinematic field-of-view eases out during sprinting; gentle motion at rest.
    var target_fov := 72.0 if (run_pressed or Input.is_action_pressed("run")) and movement_enabled else 65.0
    cam.fov = lerpf(cam.fov, target_fov, minf(1.0, delta * 2.6))''')
change(hud_path, 'hint_label.visible = not menu_open', 'hint_label.visible = not menu_open and Time.get_ticks_msec() < 13500')
change(root/'project.godot', 'CC0 Remake v0.5', 'CC0 Remake v0.6')
change(root/'export_presets.cfg','com.aurorabtw.seasons.visual05','com.aurorabtw.seasons.visual06')
change(root/'export_presets.cfg','version/code=5','version/code=6')
change(root/'export_presets.cfg','version/name="0.5"','version/name="0.6"')
change(root/'export_presets.cfg','Aurora-v0.5-Android-debug.apk','Aurora-v0.6-Android-debug.apk')
(root/'README_V06.md').write_text('''# Aurora v0.6 visual update\n\nBuilt on the working Aurora v0.5 Godot project.\n\nNew: 135 Quaternius CC0 undergrowth shrubs, batched grass plumes, natural fallen logs, sunlit pollen particles, clustered snowdrifts, additional cabin lighting, and gently animated third-person camera FOV. This is not a pixel-identical recreation of the supplied video.\n\nThe existing Quaternius and KayKit CC0 assets are retained with their original source and licensing information in docs/ASSET_SOURCES_V05.md. Source meshes are not recolored for this update. No new external downloads or accounts are needed when using the included full-source package.\n\nFor Android: Godot 4.4.1; Compatibility renderer; arm64-v8a. v0.6 package ID deliberately differs from v0.5, so both versions can be installed.\n''')
print('Applied v0.6 improvements to',root)