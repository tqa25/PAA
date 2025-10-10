extends Area3D

@export var speed: float = 22.0
@export var damage: int = 10
@export var lifetime: float = 3.0
@export var pierce: int = 0					# số mục tiêu có thể xuyên qua (0 = va là hủy)
@export var radius: float = 0.15			# bán kính “đạn” (để offset khi xuyên)
@export var proj_gravity: float = 0.0		# trọng lực tác động lên đạn (0 = bay thẳng)

# LAYER / MASK (chốt bằng code để không lệch Inspector)
@export var proj_layer: int = 1 << 3		# Layer 4 = Projectile
@export var hit_mask: int = 1 << 1			# chỉ va vào Layer 2 (Enemy)
@export var owner_layer: int = 1 << 0		# Layer 1 (Player) — chỉ dùng nếu bạn muốn bỏ qua theo layer

# truyền lúc spawn
var dir: Vector3 = Vector3.FORWARD
var proj_owner: Node = null

# nội bộ
var _alive: float = 0.0
var _vel: Vector3 = Vector3.ZERO
var _prev_pos: Vector3

func _ready() -> void:
	# ÉP layer/mask ngay khi vào scene
	collision_layer = proj_layer
	collision_mask = hit_mask

	# Bật hệ thống va chạm của Area
	monitoring = true
	monitorable = false

	# Bắt cả body lẫn area (Enemy có thể là CharacterBody3D hoặc Area3D)
	body_entered.connect(_on_body_entered)
	area_entered.connect(_on_area_entered)

	_prev_pos = global_transform.origin

	# Tự hủy sau lifetime (failsafe)
	if lifetime > 0.0:
		get_tree().create_timer(lifetime).timeout.connect(queue_free)

func setup(p_dir: Vector3, p_owner: Node) -> void:
	dir = p_dir.normalized()
	proj_owner = p_owner
	_vel = dir * speed

func _physics_process(dt: float) -> void:
	# 1) Cập nhật vận tốc (gravity nếu có)
	if proj_gravity != 0.0:
		_vel.y -= proj_gravity * dt

	# 2) Raycast chống xuyên — quét đường đi từ vị trí cũ -> mới
	var from: Vector3 = _prev_pos
	var to: Vector3 = from + _vel * dt
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state

	var params := PhysicsRayQueryParameters3D.create(from, to)
	params.collision_mask = hit_mask
	params.collide_with_bodies = true
	params.collide_with_areas = true

	# exclude PHẢI là RID (đạn + chủ đạn)
	var ex: Array[RID] = [get_rid()]
	if proj_owner != null and proj_owner is CollisionObject3D:
		ex.append((proj_owner as CollisionObject3D).get_rid())
	params.exclude = ex
	params.hit_from_inside = true

	var hit: Dictionary = space.intersect_ray(params)
	if hit:
		_on_hit_point(hit)
		return

	# 3) Không trúng -> di chuyển
	global_transform.origin = to
	_prev_pos = global_transform.origin

	# 4) TTL thủ công (phòng khi Timer bị pause)
	_alive += dt
	if lifetime > 0.0 and _alive >= lifetime:
		queue_free()

# ====== VA CHẠM SỰ KIỆN ======
func _on_body_entered(body: Node) -> void:
	# Chỉ bỏ qua chính chủ; KHÔNG bỏ qua theo owner_layer để tránh “lọt” kèo tick nhầm
	if body == proj_owner:
		return
	_apply_damage_and_finish(body)

func _on_area_entered(area: Area3D) -> void:
	if area == self or area == proj_owner:
		return
	_apply_damage_and_finish(area)

func _on_hit_point(hit: Dictionary) -> void:
	var collider: Node = hit.get("collider") as Node
	if collider and collider != proj_owner:
		_apply_damage_and_finish(collider)
	else:
		queue_free()

# ====== GÂY SÁT THƯƠNG & KẾT THÚC ======
func _apply_damage_and_finish(target: Node) -> void:
	# Gọi hàm nhận sát thương nếu có
	if target and target.has_method("take_damage"):
		target.take_damage(damage)

	# Xuyên qua N mục tiêu nếu cấu hình
	if pierce > 0:
		pierce -= 1
		# đẩy đạn qua 1 đoạn nhỏ để tránh double-hit frame sau
		global_transform.origin += dir * max(radius, 0.05)
		_prev_pos = global_transform.origin
	else:
		queue_free()
