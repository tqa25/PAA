extends CharacterBody3D

@export var move_speed: float = 6.0
@export var rotate_speed: float = 10.0
@export var projectile_scene: PackedScene	# kéo thả Projectile.tscn
@export var muzzle_offset: Vector3 = Vector3(0, 1.2, 1.8)	# cao + trước mặt lúc spawn

var input_vec: Vector2 = Vector2.ZERO			# từ joystick (-1..1)
var facing_dir: Vector3 = Vector3.FORWARD		# hướng mặt hiện tại (phẳng)

@onready var cam: Camera3D = $"../CameraRig/Camera3D"

func _physics_process(delta: float) -> void:
	# vector theo camera
	var forward := -cam.global_transform.basis.z
	forward.y = 0.0
	forward = forward.normalized()

	var right := cam.global_transform.basis.x
	right.y = 0.0
	right = right.normalized()

	var dir3 := (right * input_vec.x + forward * input_vec.y)
	if dir3.length() > 1.0:
		dir3 = dir3.normalized()

	# di chuyển
	velocity.x = dir3.x * move_speed
	velocity.z = dir3.z * move_speed
	velocity.y = 0.0
	move_and_slide()

	# xoay & ghi nhớ hướng mặt khi đang di chuyển
	if dir3.length() > 0.05:
		facing_dir = dir3
		var yaw := atan2(-dir3.x, -dir3.z)
		rotation.y = lerp_angle(rotation.y, yaw, delta * rotate_speed)

func _on_virtual_joystick_analogic_change(move: Vector2) -> void:
	# Joystick: kéo lên = tiến tới
	input_vec = Vector2(move.x, -move.y)

func fire() -> void:
	if projectile_scene == null:
		print("❌ Projectile scene chưa gán!")
		return

	# Hướng bắn = hướng mặt; nếu đứng yên thì fallback theo camera
	var shoot_dir := facing_dir.normalized()
	if shoot_dir == Vector3.ZERO:
		shoot_dir = -cam.global_transform.basis.z
		shoot_dir.y = 0.0
		shoot_dir = shoot_dir.normalized()

	# Vị trí xuất đạn: phía trước + nhấc lên (tránh dính collider Player)
	var spawn_pos: Vector3 = global_transform.origin \
		+ shoot_dir * muzzle_offset.z \
		+ Vector3(0, muzzle_offset.y, 0)

	# Tạo projectile, đặt pose trước rồi mới add vào scene (tránh lỗi not-in-tree)
	var p: Area3D = projectile_scene.instantiate()
	p.look_at_from_position(spawn_pos, spawn_pos + shoot_dir, Vector3.UP)
	get_tree().current_scene.add_child(p)

	# Truyền hướng + chủ đạn để projectile tự chạy
	if p.has_method("setup"):
		p.setup(shoot_dir, self)
