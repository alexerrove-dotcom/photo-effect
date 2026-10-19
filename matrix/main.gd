extends Node2D
var player := Vector2(640,360)
var fragments := []
var world := false
var collected := 0
var health := 100
var mission := 1
var joystick := Vector2.ZERO
var touching := false
func _ready():
 randomize()
 for i in range(5): fragments.append(Vector2(randf_range(100,1180),randf_range(100,620)))
func _process(delta):
 var motion := Input.get_vector("ui_left","ui_right","ui_up","ui_down")
 if touching: motion = joystick
 player += motion * 260 * delta
 player.x = clamp(player.x,20,1260)
 player.y = clamp(player.y,20,700)
 for i in range(fragments.size()-1,-1,-1):
  if player.distance_to(fragments[i]) < 40:
   fragments.remove_at(i)
   collected += 1
 if fragments.is_empty():
  mission += 1
  collected = 0
  for i in range(5+mission): fragments.append(Vector2(randf_range(100,1180),randf_range(100,620)))
 queue_redraw()
func _input(event):
 if event is InputEventScreenTouch:
  touching = event.pressed and event.position.x < 480
  if event.pressed and event.position.x > 1000: world = not world
  if not touching: joystick = Vector2.ZERO
 if event is InputEventScreenDrag and touching:
  joystick = (event.position - Vector2(160,570)).limit_length(100)/100
func _draw():
 draw_rect(Rect2(Vector2.ZERO,Vector2(1280,720)),Color(0.015,0.025,0.05) if not world else Color(0.02,0.08,0.04))
 for x in range(0,1280,80): draw_line(Vector2(x,0),Vector2(x,720),Color(0.05,0.25,0.32),1)
 for y in range(0,720,80): draw_line(Vector2(0,y),Vector2(1280,y),Color(0.05,0.25,0.32),1)
 for p in fragments: draw_circle(p,16,Color.CYAN if not world else Color.GREEN)
 draw_circle(player,23,Color(0.9,0.95,1.0))
 draw_arc(player,31,0,TAU,48,Color.CYAN,3)
 draw_circle(Vector2(160,570),105,Color(0.2,0.5,0.7,0.3))
 draw_rect(Rect2(1030,530,190,120),Color(0.1,0.6,0.5,0.4))
