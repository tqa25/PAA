# CameraRig.gd
# Node: CameraRig (Node3D)  └─ Camera3D (child)
# Nhiệm vụ: bám theo Player kiểu ARPG (trên cao, nhìn chéo), mượt + giới hạn map.

extends Node3D

# ---- THAM SỐ CƠ BẢN (đổi trực tiếp trong Inspector) ----
@export var target_path: NodePath             # trỏ tới Player (../Player)
@export var height: float = 5.0              # độ cao so với Player
@export var distance: float = 5.0            # lùi phía sau (tương đối theo thế giới)
@export var tilt_deg: float = 15.0            # độ nghiêng camera nhìn xuống
@export var follow_lerp: float = 8.0          # mượt bám theo (cao = bám nhanh)

# ---- GIỚI HẠN CAMERA TRONG MAP (tùy chọn) ----
@export var clamp_bounds: bool = false        # bật/tắt giới hạn
@export var half_extent: float = 90.0         # nửa kích thước map (±90 → map ~180x180)

# ---- OFFSET TINH CHỈNH (tùy chọn) ----
@export var lateral_offset: float = 0.0       # lệch ngang (trái/ phải) nếu cần
@export var forward_follow: float = 0.0       # bù trôi theo hướng chạy (0..3 là vừa)

@onready var cam: Camera3D = $Camera3D
var t: Node3D                                  # target (Player)

func _ready() -> void:
	t = get_node_or_null(target_path)
	if cam:
		cam.current = true                     # đảm bảo camera này đang active
		cam.rotation_degrees.x = -tilt_deg     # nghiêng nhìn xuống

func _physics_process(delta: float) -> void:
	if t == null:
		return

	# 1) Tính vị trí mong muốn của CameraRig (điểm treo camera)
	#    - Đặt camera cao "height" và lùi "distance" theo trục Z của thế giới
	#    - Sau đó nghiêng "tilt_deg" để nhìn xuống Player
	var desired := t.global_transform.origin \
		+ Vector3(0.0, height, distance).rotated(Vector3.LEFT, deg_to_rad(tilt_deg))

	# 1b) Bù theo hướng di chuyển của Player (tùy chọn – tạo cảm giác nhìn xa hơn phía trước)
	if forward_follow != 0.0:
		var forward := -t.global_transform.basis.z
		forward.y = 0.0
		forward = forward.normalized()
		desired += forward * forward_follow

	# 1c) Lệch ngang (tùy chọn) – view hơi lệch trái/phải
	if lateral_offset != 0.0:
		var right := t.global_transform.basis.x
		right.y = 0.0
		right = right.normalized()
		desired += right * lateral_offset

	# 2) Lerping để bám mượt
	global_transform.origin = global_transform.origin.lerp(desired, delta * follow_lerp)

	# 3) Nhìn vào Player
	cam.look_at(t.global_transform.origin, Vector3.UP)

	# 4) (Tùy chọn) Giới hạn trong map vuông ±half_extent
	if clamp_bounds:
		var p := global_transform.origin
		p.x = clampf(p.x, -half_extent, half_extent)
		p.z = clampf(p.z, -half_extent, half_extent)
		global_transform.origin = p

func _set_tilt(new_tilt: float) -> void:
	# Gọi hàm này nếu bạn muốn đổi tilt runtime
	tilt_deg = new_tilt
	if cam:
		cam.rotation_degrees.x = -tilt_deg
