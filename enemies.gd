extends CharacterBody3D

@export var hp: int = 30
@export var speed: float = 2.0

var dir: Vector3 = Vector3.FORWARD

func _ready() -> void:
	# BẮT BUỘC Enemy ở Layer 2 (1 << 1) để trúng mask của Projectile
	collision_layer = 1 << 1
	# CollisionShape3D phải tồn tại & Enabled trong scene

func _physics_process(_delta: float) -> void:
	# Di chuyển qua lại theo trục hiện tại
	velocity = dir * speed
	move_and_slide()

	# Đến biên thì đảo chiều
	if absf(position.x) > 90.0 or absf(position.z) > 90.0:
		dir = -dir

func take_damage(dmg: int) -> void:
	hp -= dmg
	if hp <= 0:
		queue_free()
