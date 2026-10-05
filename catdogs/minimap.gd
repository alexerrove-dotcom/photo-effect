extends Control

var game

func _ready() -> void:
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    set_process(true)

func _process(_delta:float) -> void:
    queue_redraw()

func _draw() -> void:
    draw_rect(Rect2(Vector2.ZERO, size), Color(0.02,0.04,0.06,0.82), true)
    draw_rect(Rect2(Vector2(8,8), size-Vector2(16,16)), Color(0.20,0.28,0.32,0.65), false, 2.0)
    for x in [0.25,0.5,0.75]:
        draw_line(Vector2(size.x*x,10), Vector2(size.x*x,size.y-10), Color(0.25,0.33,0.36,0.5), 1.0)
        draw_line(Vector2(10,size.y*x), Vector2(size.x-10,size.y*x), Color(0.25,0.33,0.36,0.5), 1.0)
    _dot(Vector3(-14,0,-14), Color("ffb331"), 7.0)
    _dot(Vector3(14,0,14), Color("ff4d4d"), 7.0)
    if game == null or not game.match_active:
        return
    if game.player_alive:
        _dot(game.player.global_position, Color("f8f8f8"), 5.0)
    for b in game.bots:
        if is_instance_valid(b) and b.alive:
            _dot(b.global_position, Color("3aa8ff") if b.team == game.player_team else Color("ff554d"), 4.0)

func _dot(world:Vector3, color:Color, radius:float) -> void:
    var p := Vector2((world.x + 30.0) / 60.0 * size.x, (world.z + 30.0) / 60.0 * size.y)
    p.x = clampf(p.x, 8.0, size.x-8.0)
    p.y = clampf(p.y, 8.0, size.y-8.0)
    draw_circle(p, radius, color)
